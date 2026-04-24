"""Tests for metric calculation and statistical analysis."""

from app.experiments.metrics import ParticipantMetrics, analyze_experiment_metrics, analyze_metric


def _rows() -> list[ParticipantMetrics]:
    return [
        ParticipantMetrics(
            user_id=1,
            variant_id=10,
            variant_key="control",
            purchase_count=1,
            revenue=100.0,
            order_values=(100.0,),
        ),
        ParticipantMetrics(
            user_id=2,
            variant_id=10,
            variant_key="control",
            purchase_count=0,
            revenue=0.0,
            order_values=(),
        ),
        ParticipantMetrics(
            user_id=3,
            variant_id=10,
            variant_key="control",
            purchase_count=1,
            revenue=50.0,
            order_values=(50.0,),
        ),
        ParticipantMetrics(
            user_id=4,
            variant_id=20,
            variant_key="treatment",
            purchase_count=2,
            revenue=220.0,
            order_values=(100.0, 120.0),
        ),
        ParticipantMetrics(
            user_id=5,
            variant_id=20,
            variant_key="treatment",
            purchase_count=1,
            revenue=80.0,
            order_values=(80.0,),
        ),
        ParticipantMetrics(
            user_id=6,
            variant_id=20,
            variant_key="treatment",
            purchase_count=0,
            revenue=0.0,
            order_values=(),
        ),
    ]


def test_conversion_rate_is_user_level_binary_metric() -> None:
    """Conversion rate should count users with at least one purchase."""
    rows = _rows()
    baseline = [row for row in rows if row.variant_key == "control"]
    compared = [row for row in rows if row.variant_key == "treatment"]

    result = analyze_metric("conversion_rate", baseline, compared)

    assert result.baseline_value == 2 / 3
    assert result.compared_value == 2 / 3
    assert result.absolute_lift == 0
    assert result.test_method == "two_proportion_ztest"


def test_arpu_and_purchase_rate_use_assigned_users_as_denominator() -> None:
    """ARPU and purchase rate should include users without purchases."""
    rows = _rows()
    baseline = [row for row in rows if row.variant_key == "control"]
    compared = [row for row in rows if row.variant_key == "treatment"]

    arpu = analyze_metric("average_revenue_per_user", baseline, compared)
    purchase_rate = analyze_metric("purchase_rate", baseline, compared)

    assert arpu.baseline_value == 50.0
    assert arpu.compared_value == 100.0
    assert purchase_rate.baseline_value == 2 / 3
    assert purchase_rate.compared_value == 1.0


def test_aov_uses_orders_as_denominator() -> None:
    """Average order value should be calculated over purchase events."""
    rows = _rows()
    baseline = [row for row in rows if row.variant_key == "control"]
    compared = [row for row in rows if row.variant_key == "treatment"]

    result = analyze_metric("average_order_value", baseline, compared)

    assert result.sample_size_baseline == 2
    assert result.sample_size_compared == 3
    assert result.baseline_value == 75.0
    assert result.compared_value == 100.0


def test_analyze_experiment_metrics_returns_all_supported_metrics() -> None:
    """Full analysis should return four metrics for one treatment comparison."""
    results = analyze_experiment_metrics(_rows())

    assert len(results) == 4
    assert {result.metric_key for result in results} == {
        "conversion_rate",
        "average_revenue_per_user",
        "average_order_value",
        "purchase_rate",
    }


def test_relative_lift_is_none_when_control_value_is_zero() -> None:
    """Relative lift should not divide by zero."""
    baseline = [
        ParticipantMetrics(1, 10, "control", 0, 0.0, ()),
        ParticipantMetrics(2, 10, "control", 0, 0.0, ()),
    ]
    compared = [
        ParticipantMetrics(3, 20, "treatment", 1, 50.0, (50.0,)),
        ParticipantMetrics(4, 20, "treatment", 0, 0.0, ()),
    ]

    result = analyze_metric("average_revenue_per_user", baseline, compared)

    assert result.baseline_value == 0.0
    assert result.compared_value == 25.0
    assert result.relative_lift is None
