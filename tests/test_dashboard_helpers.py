"""Tests for pure Streamlit dashboard helper functions."""

from dashboard.helpers import (
    build_result_summary,
    format_metric_value,
    metric_label,
    normalize_demo_check,
    status_label,
)


def test_status_label_translates_known_statuses() -> None:
    """Experiment statuses should be shown in Russian."""
    assert status_label("running") == "Запущен"
    assert status_label("completed") == "Завершен"
    assert status_label("draft") == "Черновик"
    assert status_label("paused") == "Приостановлен"


def test_metric_label_translates_product_metrics() -> None:
    """Metric keys should be readable for a Russian demo audience."""
    assert metric_label("conversion_rate") == "Конверсия"
    assert metric_label("average_revenue_per_user") == "ARPU"
    assert metric_label("average_order_value") == "Средний чек"
    assert metric_label("purchase_rate") == "Частота покупок"


def test_format_metric_value_uses_business_formatting() -> None:
    """Metrics should be formatted according to their meaning."""
    assert format_metric_value("conversion_rate", 0.1234) == "12.34%"
    assert format_metric_value("average_revenue_per_user", 12.5) == "$12.50"
    assert format_metric_value("purchase_rate", 0.8754) == "0.875"


def test_build_result_summary_handles_missing_results() -> None:
    """Empty saved results should produce a clear warning message."""
    summary, tone = build_result_summary([])

    assert tone == "warning"
    assert "Сохраненных результатов анализа пока нет" in summary
    assert "POST /experiments/{key}/analyze" in summary


def test_build_result_summary_handles_non_significant_uplift() -> None:
    """Non-significant effects should not be described as winners."""
    summary, tone = build_result_summary(
        [
            {
                "metric_key": "conversion_rate",
                "absolute_lift": 0.03,
                "p_value": 0.21,
                "is_significant": False,
            }
        ]
    )

    assert tone == "neutral"
    assert "не является статистически значимым" in summary
    assert "Вариант B улучшил" in summary


def test_build_result_summary_handles_significant_winner() -> None:
    """A significant positive effect should be described as a winner."""
    summary, tone = build_result_summary(
        [
            {
                "metric_key": "conversion_rate",
                "absolute_lift": 0.08,
                "p_value": 0.01,
                "is_significant": True,
            }
        ]
    )

    assert tone == "success"
    assert "статистически значимое улучшение" in summary
    assert "победителя" in summary


def test_normalize_demo_check_returns_russian_statuses() -> None:
    """Demo checks should use clear Russian statuses."""
    success = normalize_demo_check("API", True, "УСПЕХ: API доступен")
    warning = normalize_demo_check(
        "Results",
        True,
        "ok",
        warning=True,
        warning_message="ПРЕДУПРЕЖДЕНИЕ: результатов пока нет",
    )
    error = normalize_demo_check(
        "Events",
        False,
        "ok",
        error_message="ОШИБКА: события не загружены",
    )

    assert success["Статус"] == "УСПЕХ"
    assert warning["Статус"] == "ПРЕДУПРЕЖДЕНИЕ"
    assert error["Статус"] == "ОШИБКА"
