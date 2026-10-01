"""Tests for experiment design: sample size, power, MDE, SRM, CUPED, Holm."""

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.experiments.design import (
    cuped_adjust,
    cuped_ttest,
    holm_adjust,
    minimum_detectable_effect,
    power_two_proportions,
    sample_ratio_mismatch,
    sample_size_two_proportions,
)
from app.main import app

client = TestClient(app)


def test_sample_size_matches_reference_value() -> None:
    """10% -> 11% at alpha 0.05 and power 0.8 needs about 14.7k users per group."""
    plan = sample_size_two_proportions(baseline_rate=0.10, mde_relative=0.10)

    assert 14_700 <= plan.users_control <= 14_800
    assert plan.users_treatment == plan.users_control
    assert plan.expected_rate == pytest.approx(0.11)


def test_planned_sample_reaches_target_power() -> None:
    plan = sample_size_two_proportions(baseline_rate=0.134, mde_relative=0.05, power=0.8)
    achieved = power_two_proportions(
        plan.baseline_rate, plan.expected_rate, plan.users_control, plan.users_treatment
    )
    smaller = power_two_proportions(
        plan.baseline_rate,
        plan.expected_rate,
        int(plan.users_control * 0.9),
        int(plan.users_treatment * 0.9),
    )

    assert achieved == pytest.approx(0.8, abs=0.005)
    assert smaller < 0.8


def test_unequal_split_needs_more_users_in_total() -> None:
    equal = sample_size_two_proportions(0.2, 0.1)
    skewed = sample_size_two_proportions(0.2, 0.1, treatment_ratio=0.25)

    assert skewed.users_total > equal.users_total


def test_mde_is_consistent_with_sample_size() -> None:
    plan = sample_size_two_proportions(baseline_rate=0.134, mde_relative=0.07)
    mde = minimum_detectable_effect(0.134, plan.users_control)

    assert mde == pytest.approx(0.07, rel=0.02)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"baseline_rate": 0, "mde_relative": 0.1},
        {"baseline_rate": 0.5, "mde_relative": 0},
        {"baseline_rate": 0.9, "mde_relative": 0.2},
        {"baseline_rate": 0.1, "mde_relative": 0.1, "treatment_ratio": 0},
    ],
)
def test_sample_size_rejects_invalid_input(kwargs: dict) -> None:
    with pytest.raises(ValueError):
        sample_size_two_proportions(**kwargs)


def test_srm_not_flagged_for_small_imbalance() -> None:
    result = sample_ratio_mismatch({"control": 10_000, "treatment": 10_150})

    assert result.p_value > 0.001
    assert not result.has_mismatch


def test_srm_flagged_for_broken_split() -> None:
    result = sample_ratio_mismatch({"control": 10_000, "treatment": 10_600})

    assert result.chi_square == pytest.approx(2 * 300**2 / 10_300)
    assert result.has_mismatch


def test_srm_uses_planned_shares() -> None:
    result = sample_ratio_mismatch(
        {"control": 8_000, "treatment": 2_000},
        expected_shares={"control": 0.8, "treatment": 0.2},
    )

    assert result.chi_square == pytest.approx(0)
    assert not result.has_mismatch


def test_srm_rejects_wrong_shares() -> None:
    with pytest.raises(ValueError):
        sample_ratio_mismatch({"a": 1, "b": 1}, expected_shares={"a": 0.7, "b": 0.7})


def _correlated_sample(rng: np.random.Generator, size: int, effect: float):
    pre_period = rng.normal(100, 20, size)
    metric = 0.8 * pre_period + rng.normal(0, 12, size) + effect
    return metric.tolist(), pre_period.tolist()


def test_cuped_keeps_mean_and_reduces_variance() -> None:
    rng = np.random.default_rng(7)
    metric, covariate = _correlated_sample(rng, 5_000, effect=0)
    adjusted, theta = cuped_adjust(metric, covariate)

    assert theta == pytest.approx(0.8, abs=0.05)
    assert np.mean(adjusted) == pytest.approx(np.mean(metric))
    assert np.var(adjusted) < 0.4 * np.var(metric)


def test_cuped_ttest_finds_effect_raw_test_misses() -> None:
    rng = np.random.default_rng(42)
    control_y, control_x = _correlated_sample(rng, 1_500, effect=0)
    treatment_y, treatment_x = _correlated_sample(rng, 1_500, effect=1.5)

    result = cuped_ttest(control_y, control_x, treatment_y, treatment_x)

    assert result.variance_reduction > 0.6
    assert result.p_value < 0.05
    assert result.p_value < result.raw_p_value
    assert result.ci_lower < 1.5 < result.ci_upper


def test_cuped_requires_matching_lengths() -> None:
    with pytest.raises(ValueError):
        cuped_adjust([1.0, 2.0], [1.0])


def test_holm_adjustment_reference_values() -> None:
    adjusted = holm_adjust({"cr": 0.01, "arpu": 0.04, "aov": 0.03})

    assert adjusted["cr"] == pytest.approx(0.03)
    assert adjusted["aov"] == pytest.approx(0.06)
    assert adjusted["arpu"] == pytest.approx(0.06)


def test_sample_size_endpoint() -> None:
    response = client.post(
        "/design/sample-size", json={"baseline_rate": 0.1, "mde_relative": 0.1}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["users_total"] == body["users_control"] + body["users_treatment"]
    assert 14_700 <= body["users_control"] <= 14_800


def test_sample_size_endpoint_rejects_unreachable_rate() -> None:
    response = client.post(
        "/design/sample-size", json={"baseline_rate": 0.9, "mde_relative": 0.5}
    )

    assert response.status_code == 422


def test_srm_endpoint() -> None:
    response = client.post(
        "/design/srm-check", json={"observed": {"control": 10_000, "treatment": 10_600}}
    )

    assert response.status_code == 200
    assert response.json()["has_mismatch"] is True
