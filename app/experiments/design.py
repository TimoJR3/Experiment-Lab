"""Experiment design and validity checks.

Covers the questions that come before and around the main metric test:
how many users are needed (sample size / power / MDE), whether the split
itself is healthy (sample ratio mismatch), how to reduce variance with
pre-experiment data (CUPED) and how to control false positives when several
metrics or variants are compared at once (Holm correction).
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil, sqrt
from statistics import mean

from scipy import stats


def _z(probability: float) -> float:
    return float(stats.norm.ppf(probability))


def _validate_rate(name: str, value: float) -> None:
    if not 0 < value < 1:
        raise ValueError(f"{name} must be between 0 and 1, got {value}")


@dataclass(frozen=True, slots=True)
class SampleSizePlan:
    """Required users for a two-sided test of two proportions."""

    baseline_rate: float
    expected_rate: float
    mde_absolute: float
    mde_relative: float
    alpha: float
    power: float
    treatment_ratio: float
    users_control: int
    users_treatment: int

    @property
    def users_total(self) -> int:
        return self.users_control + self.users_treatment


def sample_size_two_proportions(
    baseline_rate: float,
    mde_relative: float,
    alpha: float = 0.05,
    power: float = 0.8,
    treatment_ratio: float = 1.0,
) -> SampleSizePlan:
    """Users per group to detect a relative lift of a conversion rate.

    Uses the normal approximation with unpooled variances:
    n_c = (z_{1-a/2} + z_{power})^2 * (p1(1-p1) + p2(1-p2)/k) / (p2 - p1)^2,
    n_t = k * n_c, where k is treatment_ratio.
    """
    _validate_rate("baseline_rate", baseline_rate)
    _validate_rate("alpha", alpha)
    _validate_rate("power", power)
    if mde_relative == 0:
        raise ValueError("mde_relative must not be zero")
    if treatment_ratio <= 0:
        raise ValueError("treatment_ratio must be positive")

    expected_rate = baseline_rate * (1 + mde_relative)
    _validate_rate("expected_rate", expected_rate)

    z_total = _z(1 - alpha / 2) + _z(power)
    variance_term = (
        baseline_rate * (1 - baseline_rate)
        + expected_rate * (1 - expected_rate) / treatment_ratio
    )
    users_control = ceil(z_total**2 * variance_term / (expected_rate - baseline_rate) ** 2)
    users_treatment = ceil(users_control * treatment_ratio)

    return SampleSizePlan(
        baseline_rate=baseline_rate,
        expected_rate=expected_rate,
        mde_absolute=expected_rate - baseline_rate,
        mde_relative=mde_relative,
        alpha=alpha,
        power=power,
        treatment_ratio=treatment_ratio,
        users_control=users_control,
        users_treatment=users_treatment,
    )


def power_two_proportions(
    baseline_rate: float,
    expected_rate: float,
    users_control: int,
    users_treatment: int,
    alpha: float = 0.05,
) -> float:
    """Probability to detect the difference with a two-sided z-test."""
    _validate_rate("baseline_rate", baseline_rate)
    _validate_rate("expected_rate", expected_rate)
    if users_control <= 0 or users_treatment <= 0:
        raise ValueError("group sizes must be positive")

    standard_error = sqrt(
        baseline_rate * (1 - baseline_rate) / users_control
        + expected_rate * (1 - expected_rate) / users_treatment
    )
    shift = abs(expected_rate - baseline_rate) / standard_error
    z_alpha = _z(1 - alpha / 2)
    return float(stats.norm.cdf(shift - z_alpha) + stats.norm.cdf(-shift - z_alpha))


def minimum_detectable_effect(
    baseline_rate: float,
    users_per_group: int,
    alpha: float = 0.05,
    power: float = 0.8,
) -> float:
    """Smallest relative lift detectable with equal groups of the given size.

    Solved by bisection on the power function, so it stays consistent with
    power_two_proportions instead of relying on a second approximation.
    """
    _validate_rate("baseline_rate", baseline_rate)
    if users_per_group <= 0:
        raise ValueError("users_per_group must be positive")

    low, high = 1e-6, (1 - baseline_rate) / baseline_rate - 1e-9
    if power_two_proportions(
        baseline_rate, baseline_rate * (1 + high), users_per_group, users_per_group, alpha
    ) < power:
        raise ValueError("required power is not reachable with this sample size")

    for _ in range(100):
        middle = (low + high) / 2
        achieved = power_two_proportions(
            baseline_rate,
            baseline_rate * (1 + middle),
            users_per_group,
            users_per_group,
            alpha,
        )
        if achieved < power:
            low = middle
        else:
            high = middle
    return high


@dataclass(frozen=True, slots=True)
class SrmResult:
    """Sample ratio mismatch check for the assignment split."""

    observed: dict[str, int]
    expected_shares: dict[str, float]
    chi_square: float
    p_value: float
    threshold: float

    @property
    def has_mismatch(self) -> bool:
        return self.p_value < self.threshold


def sample_ratio_mismatch(
    observed: dict[str, int],
    expected_shares: dict[str, float] | None = None,
    threshold: float = 0.001,
) -> SrmResult:
    """Chi-square goodness-of-fit test of observed group sizes.

    A strict threshold (0.001) is the common industry default: SRM means the
    split or logging is broken, so the metric results should not be trusted.
    """
    if len(observed) < 2:
        raise ValueError("at least two groups are required")
    if any(count < 0 for count in observed.values()):
        raise ValueError("group sizes must be non-negative")

    total = sum(observed.values())
    if total == 0:
        raise ValueError("no assigned users")

    if expected_shares is None:
        expected_shares = {key: 1 / len(observed) for key in observed}
    if set(expected_shares) != set(observed):
        raise ValueError("expected_shares must have the same groups as observed")
    share_sum = sum(expected_shares.values())
    if abs(share_sum - 1) > 1e-9:
        raise ValueError("expected shares must sum to 1")

    keys = sorted(observed)
    chi_square, p_value = stats.chisquare(
        [observed[key] for key in keys],
        [expected_shares[key] * total for key in keys],
    )
    return SrmResult(
        observed=dict(observed),
        expected_shares=dict(expected_shares),
        chi_square=float(chi_square),
        p_value=float(p_value),
        threshold=threshold,
    )


@dataclass(frozen=True, slots=True)
class CupedResult:
    """Treatment effect estimated on CUPED-adjusted metric values."""

    theta: float
    effect: float
    ci_lower: float
    ci_upper: float
    p_value: float
    variance_reduction: float
    raw_p_value: float


def cuped_adjust(
    metric: list[float],
    covariate: list[float],
    theta: float | None = None,
) -> tuple[list[float], float]:
    """Return metric values adjusted by a pre-experiment covariate.

    y_adj = y - theta * (x - mean(x)), theta = cov(x, y) / var(x).
    The adjustment keeps the mean of y and removes the variance explained by x.
    """
    if len(metric) != len(covariate):
        raise ValueError("metric and covariate must have the same length")
    if len(metric) < 2:
        raise ValueError("at least two observations are required")

    covariate_mean = mean(covariate)
    if theta is None:
        metric_mean = mean(metric)
        covariance = sum(
            (x - covariate_mean) * (y - metric_mean) for x, y in zip(covariate, metric)
        )
        covariate_variance = sum((x - covariate_mean) ** 2 for x in covariate)
        theta = covariance / covariate_variance if covariate_variance else 0.0

    adjusted = [y - theta * (x - covariate_mean) for x, y in zip(covariate, metric)]
    return adjusted, theta


def cuped_ttest(
    control_metric: list[float],
    control_covariate: list[float],
    treatment_metric: list[float],
    treatment_covariate: list[float],
    alpha: float = 0.05,
) -> CupedResult:
    """Welch t-test on CUPED-adjusted values with one theta for both groups.

    Theta and the covariate mean are estimated on the pooled sample so that
    both groups are adjusted identically and the effect stays unbiased.
    """
    pooled_metric = control_metric + treatment_metric
    pooled_covariate = control_covariate + treatment_covariate
    pooled_adjusted, theta = cuped_adjust(pooled_metric, pooled_covariate)

    control_adjusted = pooled_adjusted[: len(control_metric)]
    treatment_adjusted = pooled_adjusted[len(control_metric) :]

    adjusted_test = stats.ttest_ind(treatment_adjusted, control_adjusted, equal_var=False)
    raw_test = stats.ttest_ind(treatment_metric, control_metric, equal_var=False)

    effect = mean(treatment_adjusted) - mean(control_adjusted)
    interval = adjusted_test.confidence_interval(confidence_level=1 - alpha)

    raw_variance = stats.tvar(pooled_metric)
    adjusted_variance = stats.tvar(pooled_adjusted)
    variance_reduction = 1 - adjusted_variance / raw_variance if raw_variance else 0.0

    return CupedResult(
        theta=float(theta),
        effect=float(effect),
        ci_lower=float(interval.low),
        ci_upper=float(interval.high),
        p_value=float(adjusted_test.pvalue),
        variance_reduction=float(variance_reduction),
        raw_p_value=float(raw_test.pvalue),
    )


def holm_adjust(p_values: dict[str, float]) -> dict[str, float]:
    """Holm-Bonferroni adjusted p-values (controls family-wise error rate)."""
    ordered = sorted(p_values.items(), key=lambda item: item[1])
    total = len(ordered)
    adjusted: dict[str, float] = {}
    running_max = 0.0
    for rank, (key, p_value) in enumerate(ordered):
        running_max = max(running_max, min(1.0, (total - rank) * p_value))
        adjusted[key] = running_max
    return adjusted
