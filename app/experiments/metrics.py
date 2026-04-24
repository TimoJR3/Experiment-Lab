"""Metric calculation and basic statistical tests for experiments."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from statistics import mean, variance
from typing import Any

from scipy import stats
from statsmodels.stats.proportion import proportions_ztest


@dataclass(frozen=True, slots=True)
class ParticipantMetrics:
    """User-level metrics used as input for experiment analysis."""

    user_id: int
    variant_id: int
    variant_key: str
    purchase_count: int
    revenue: float
    order_values: tuple[float, ...]

    @property
    def converted(self) -> int:
        """Return 1 when a user has at least one purchase."""
        return int(self.purchase_count > 0)


@dataclass(frozen=True, slots=True)
class MetricAnalysisResult:
    """Analysis result for one metric and one variant comparison."""

    metric_key: str
    metric_name: str
    metric_type: str
    baseline_variant_id: int
    baseline_variant_key: str
    compared_variant_id: int
    compared_variant_key: str
    sample_size_baseline: int
    sample_size_compared: int
    baseline_value: float
    compared_value: float
    absolute_lift: float
    relative_lift: float | None
    p_value: float | None
    ci_lower: float | None
    ci_upper: float | None
    is_significant: bool | None
    test_method: str
    result_payload: dict[str, Any]


SUPPORTED_METRICS = {
    "conversion_rate": {
        "metric_name": "Conversion Rate",
        "metric_type": "conversion",
        "source_event_name": "purchase",
        "description": "Share of assigned users with at least one purchase.",
    },
    "average_revenue_per_user": {
        "metric_name": "Average Revenue Per User",
        "metric_type": "mean",
        "source_event_name": "purchase",
        "description": "Average purchase revenue per assigned user.",
    },
    "average_order_value": {
        "metric_name": "Average Order Value",
        "metric_type": "mean",
        "source_event_name": "purchase",
        "description": "Average revenue per purchase event.",
    },
    "purchase_rate": {
        "metric_name": "Purchase Rate",
        "metric_type": "mean",
        "source_event_name": "purchase",
        "description": "Average number of purchase events per assigned user.",
    },
}


def _relative_lift(baseline_value: float, compared_value: float) -> float | None:
    """Calculate relative lift with zero-baseline protection."""
    if baseline_value == 0:
        return None
    return (compared_value - baseline_value) / baseline_value


def _normal_ci_for_proportion_diff(
    baseline_successes: int,
    compared_successes: int,
    baseline_n: int,
    compared_n: int,
) -> tuple[float | None, float | None]:
    """Calculate a simple 95% CI for difference in proportions."""
    if baseline_n == 0 or compared_n == 0:
        return None, None

    baseline_rate = baseline_successes / baseline_n
    compared_rate = compared_successes / compared_n
    standard_error = sqrt(
        baseline_rate * (1 - baseline_rate) / baseline_n
        + compared_rate * (1 - compared_rate) / compared_n
    )
    if standard_error == 0:
        return None, None

    diff = compared_rate - baseline_rate
    margin = 1.96 * standard_error
    return diff - margin, diff + margin


def _proportion_ztest(
    baseline_values: list[int],
    compared_values: list[int],
) -> tuple[float | None, float | None, float | None]:
    """Run a two-sided z-test for two independent proportions."""
    baseline_n = len(baseline_values)
    compared_n = len(compared_values)
    baseline_successes = sum(baseline_values)
    compared_successes = sum(compared_values)

    ci_lower, ci_upper = _normal_ci_for_proportion_diff(
        baseline_successes=baseline_successes,
        compared_successes=compared_successes,
        baseline_n=baseline_n,
        compared_n=compared_n,
    )

    if baseline_n == 0 or compared_n == 0:
        return None, ci_lower, ci_upper

    try:
        _, p_value = proportions_ztest(
            count=[compared_successes, baseline_successes],
            nobs=[compared_n, baseline_n],
            alternative="two-sided",
        )
    except Exception:
        p_value = None

    if p_value != p_value:
        p_value = None

    return p_value, ci_lower, ci_upper


def _welch_ttest(
    baseline_values: list[float],
    compared_values: list[float],
) -> tuple[float | None, float | None, float | None]:
    """Run Welch's t-test and return p-value plus 95% CI for mean difference."""
    if len(baseline_values) < 2 or len(compared_values) < 2:
        return None, None, None

    baseline_mean = mean(baseline_values)
    compared_mean = mean(compared_values)
    baseline_variance = variance(baseline_values)
    compared_variance = variance(compared_values)
    standard_error = sqrt(
        baseline_variance / len(baseline_values)
        + compared_variance / len(compared_values)
    )

    if standard_error == 0:
        p_value = 1.0 if baseline_mean == compared_mean else None
        return p_value, None, None

    numerator = standard_error**4
    denominator = (
        (baseline_variance / len(baseline_values)) ** 2 / (len(baseline_values) - 1)
        + (compared_variance / len(compared_values)) ** 2 / (len(compared_values) - 1)
    )
    degrees_of_freedom = numerator / denominator if denominator else 1
    diff = compared_mean - baseline_mean
    margin = stats.t.ppf(0.975, degrees_of_freedom) * standard_error

    t_statistic = diff / standard_error
    p_value = float(2 * stats.t.sf(abs(t_statistic), degrees_of_freedom))

    return p_value, diff - margin, diff + margin


def _build_result(
    metric_key: str,
    baseline_rows: list[ParticipantMetrics],
    compared_rows: list[ParticipantMetrics],
    baseline_values: list[float] | list[int],
    compared_values: list[float] | list[int],
    p_value: float | None,
    ci_lower: float | None,
    ci_upper: float | None,
    test_method: str,
    sample_size_baseline: int | None = None,
    sample_size_compared: int | None = None,
) -> MetricAnalysisResult:
    """Create a normalized analysis result."""
    metric_info = SUPPORTED_METRICS[metric_key]
    baseline_value = mean(baseline_values) if baseline_values else 0.0
    compared_value = mean(compared_values) if compared_values else 0.0
    absolute_lift = compared_value - baseline_value
    relative_lift = _relative_lift(baseline_value, compared_value)
    is_significant = None if p_value is None else p_value < 0.05

    return MetricAnalysisResult(
        metric_key=metric_key,
        metric_name=str(metric_info["metric_name"]),
        metric_type=str(metric_info["metric_type"]),
        baseline_variant_id=baseline_rows[0].variant_id,
        baseline_variant_key=baseline_rows[0].variant_key,
        compared_variant_id=compared_rows[0].variant_id,
        compared_variant_key=compared_rows[0].variant_key,
        sample_size_baseline=sample_size_baseline or len(baseline_values),
        sample_size_compared=sample_size_compared or len(compared_values),
        baseline_value=float(baseline_value),
        compared_value=float(compared_value),
        absolute_lift=float(absolute_lift),
        relative_lift=None if relative_lift is None else float(relative_lift),
        p_value=None if p_value is None else float(p_value),
        ci_lower=None if ci_lower is None else float(ci_lower),
        ci_upper=None if ci_upper is None else float(ci_upper),
        is_significant=is_significant,
        test_method=test_method,
        result_payload={
            "baseline_variant_key": baseline_rows[0].variant_key,
            "compared_variant_key": compared_rows[0].variant_key,
            "alpha": 0.05,
        },
    )


def _analyze_conversion_rate(
    baseline_rows: list[ParticipantMetrics],
    compared_rows: list[ParticipantMetrics],
) -> MetricAnalysisResult:
    """Analyze conversion rate as a binary user-level metric."""
    baseline_values = [row.converted for row in baseline_rows]
    compared_values = [row.converted for row in compared_rows]
    p_value, ci_lower, ci_upper = _proportion_ztest(baseline_values, compared_values)
    return _build_result(
        metric_key="conversion_rate",
        baseline_rows=baseline_rows,
        compared_rows=compared_rows,
        baseline_values=baseline_values,
        compared_values=compared_values,
        p_value=p_value,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        test_method="two_proportion_ztest",
    )


def _analyze_user_mean_metric(
    metric_key: str,
    baseline_rows: list[ParticipantMetrics],
    compared_rows: list[ParticipantMetrics],
) -> MetricAnalysisResult:
    """Analyze a user-level numeric metric with Welch's t-test."""
    if metric_key == "average_revenue_per_user":
        baseline_values = [row.revenue for row in baseline_rows]
        compared_values = [row.revenue for row in compared_rows]
    elif metric_key == "purchase_rate":
        baseline_values = [float(row.purchase_count) for row in baseline_rows]
        compared_values = [float(row.purchase_count) for row in compared_rows]
    else:
        raise ValueError(f"unsupported user metric: {metric_key}")

    p_value, ci_lower, ci_upper = _welch_ttest(baseline_values, compared_values)
    return _build_result(
        metric_key=metric_key,
        baseline_rows=baseline_rows,
        compared_rows=compared_rows,
        baseline_values=baseline_values,
        compared_values=compared_values,
        p_value=p_value,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        test_method="welch_ttest",
    )


def _analyze_average_order_value(
    baseline_rows: list[ParticipantMetrics],
    compared_rows: list[ParticipantMetrics],
) -> MetricAnalysisResult:
    """Analyze average order value as an order-level metric."""
    baseline_values = [value for row in baseline_rows for value in row.order_values]
    compared_values = [value for row in compared_rows for value in row.order_values]
    p_value, ci_lower, ci_upper = _welch_ttest(baseline_values, compared_values)
    return _build_result(
        metric_key="average_order_value",
        baseline_rows=baseline_rows,
        compared_rows=compared_rows,
        baseline_values=baseline_values,
        compared_values=compared_values,
        p_value=p_value,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        test_method="welch_ttest",
        sample_size_baseline=len(baseline_values),
        sample_size_compared=len(compared_values),
    )


def analyze_metric(
    metric_key: str,
    baseline_rows: list[ParticipantMetrics],
    compared_rows: list[ParticipantMetrics],
) -> MetricAnalysisResult:
    """Analyze one supported metric for a control/treatment comparison."""
    if not baseline_rows or not compared_rows:
        raise ValueError("baseline and compared groups must not be empty")

    if metric_key == "conversion_rate":
        return _analyze_conversion_rate(baseline_rows, compared_rows)

    if metric_key in {"average_revenue_per_user", "purchase_rate"}:
        return _analyze_user_mean_metric(metric_key, baseline_rows, compared_rows)

    if metric_key == "average_order_value":
        return _analyze_average_order_value(baseline_rows, compared_rows)

    raise ValueError(f"unsupported metric: {metric_key}")


def analyze_experiment_metrics(
    participant_rows: list[ParticipantMetrics],
    metric_keys: list[str] | None = None,
    control_variant_key: str = "control",
) -> list[MetricAnalysisResult]:
    """Analyze supported metrics for control against every non-control variant."""
    selected_metrics = metric_keys or list(SUPPORTED_METRICS)
    rows_by_variant: dict[str, list[ParticipantMetrics]] = {}

    for row in participant_rows:
        rows_by_variant.setdefault(row.variant_key, []).append(row)

    baseline_rows = rows_by_variant.get(control_variant_key)
    if not baseline_rows:
        raise ValueError("control group is empty or missing")

    results: list[MetricAnalysisResult] = []
    for variant_key, compared_rows in rows_by_variant.items():
        if variant_key == control_variant_key:
            continue
        for metric_key in selected_metrics:
            results.append(
                analyze_metric(
                    metric_key=metric_key,
                    baseline_rows=baseline_rows,
                    compared_rows=compared_rows,
                )
            )

    return results
