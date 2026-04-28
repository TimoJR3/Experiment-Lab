"""Pure helper functions for the Russian Streamlit dashboard."""

from __future__ import annotations

from typing import Any

STATUS_LABELS = {
    "draft": "Черновик",
    "running": "Запущен",
    "completed": "Завершен",
    "paused": "Приостановлен",
}

STATUS_CSS_CLASSES = {
    "draft": "badge-draft",
    "running": "badge-running",
    "completed": "badge-completed",
    "paused": "badge-paused",
}

METRIC_LABELS = {
    "conversion_rate": "Конверсия",
    "average_revenue_per_user": "ARPU",
    "average_order_value": "Средний чек",
    "purchase_rate": "Частота покупок",
}

METRIC_CAPTIONS = {
    "conversion_rate": "Доля участников, которые совершили покупку.",
    "average_revenue_per_user": "Средняя выручка на назначенного пользователя.",
    "average_order_value": "Средняя сумма одного purchase-события.",
    "purchase_rate": "Среднее число покупок на одного участника.",
}

EVENT_LABELS = {
    "app_open": "Открытие приложения",
    "view_item": "Просмотр товара",
    "add_to_cart": "Добавление в корзину",
    "purchase": "Покупка",
    "subscription_start": "Старт подписки",
    "subscription_renewal": "Продление подписки",
}


def status_label(status: str | None) -> str:
    """Return a Russian label for an experiment status."""
    if not status:
        return "Неизвестно"
    return STATUS_LABELS.get(status, status)


def status_badge_class(status: str | None) -> str:
    """Return CSS class for an experiment status badge."""
    if not status:
        return "badge-draft"
    return STATUS_CSS_CLASSES.get(status, "badge-draft")


def metric_label(metric_key: str | None) -> str:
    """Return a Russian label for a metric key."""
    if not metric_key:
        return "Метрика"
    return METRIC_LABELS.get(metric_key, metric_key)


def metric_caption(metric_key: str | None) -> str:
    """Return a short Russian explanation for a metric."""
    if not metric_key:
        return "Описание метрики недоступно."
    return METRIC_CAPTIONS.get(metric_key, "Пользовательская метрика эксперимента.")


def event_label(event_name: str | None) -> str:
    """Return a Russian label for a product event."""
    if not event_name:
        return "Неизвестное событие"
    return EVENT_LABELS.get(event_name, event_name)


def format_ratio(value: float | int | None) -> str:
    """Format a ratio as a percentage for UI display."""
    if value is None:
        return "н/д"
    return f"{float(value) * 100:.2f}%"


def format_number(value: float | int | None, digits: int = 4) -> str:
    """Format a numeric value for compact tables."""
    if value is None:
        return "н/д"
    return f"{float(value):.{digits}f}"


def format_money(value: float | int | None) -> str:
    """Format money-like values used by the synthetic revenue data."""
    if value is None:
        return "н/д"
    return f"${float(value):,.2f}"


def format_metric_value(metric_key: str, value: float | int | None) -> str:
    """Format metric values based on their business meaning."""
    if value is None:
        return "н/д"
    if metric_key == "conversion_rate":
        return format_ratio(value)
    if metric_key in {"average_revenue_per_user", "average_order_value"}:
        return format_money(value)
    return format_number(value, digits=3)


def confidence_interval_text(row: dict[str, Any]) -> str:
    """Build a compact Russian confidence interval string."""
    lower = row.get("ci_lower")
    upper = row.get("ci_upper")
    if lower is None or upper is None:
        return "н/д"
    return f"[{float(lower):.4f}; {float(upper):.4f}]"


def significance_label(value: bool | None) -> str:
    """Translate statistical significance to a Russian table value."""
    if value is True:
        return "Да"
    if value is False:
        return "Нет"
    return "н/д"


def relative_lift_text(value: float | int | None) -> str:
    """Format relative lift as a percentage."""
    if value is None:
        return "н/д"
    return format_ratio(value)


def build_result_summary(results: list[dict[str, Any]]) -> tuple[str, str]:
    """Create a plain-language Russian A/B test interpretation."""
    if not results:
        return (
            "Сохраненных результатов анализа пока нет. "
            "Запустите POST /experiments/{key}/analyze, чтобы сохранить "
            "p-value, доверительные интервалы и итоговый вывод.",
            "warning",
        )

    significant_rows = [row for row in results if row.get("is_significant") is True]
    if not significant_rows:
        best = max(results, key=lambda row: abs(row.get("absolute_lift") or 0))
        metric_name = metric_label(str(best.get("metric_key")))
        lift = best.get("absolute_lift")
        p_value = best.get("p_value")
        direction = "улучшил" if (lift or 0) > 0 else "ухудшил"
        return (
            f"Вариант B {direction} метрику «{metric_name}», но результат "
            f"пока не является статистически значимым. "
            f"Наблюдаемый эффект: {format_number(lift)}, "
            f"p-value: {format_number(p_value)}. "
            "Такой результат стоит трактовать как сигнал, а не как "
            "доказанное бизнес-решение.",
            "neutral",
        )

    best = max(significant_rows, key=lambda row: abs(row.get("absolute_lift") or 0))
    metric_name = metric_label(str(best.get("metric_key")))
    lift = best.get("absolute_lift")
    p_value = best.get("p_value")
    if (lift or 0) > 0:
        return (
            f"Вариант B показал статистически значимое улучшение по метрике "
            f"«{metric_name}». Его можно рассматривать как победителя "
            f"для этой метрики. Эффект: {format_number(lift)}, "
            f"p-value: {format_number(p_value)}.",
            "success",
        )
    return (
        f"Вариант B статистически значимо ухудшил метрику «{metric_name}». "
        f"Такой вариант не стоит раскатывать без доработки. "
        f"Эффект: {format_number(lift)}, p-value: {format_number(p_value)}.",
        "danger",
    )


def normalize_demo_check(
    name: str,
    passed: bool,
    success_message: str,
    warning_message: str | None = None,
    error_message: str | None = None,
    warning: bool = False,
) -> dict[str, str]:
    """Normalize one demo smoke check into a display row."""
    if warning:
        return {
            "Проверка": name,
            "Статус": "ПРЕДУПРЕЖДЕНИЕ",
            "Сообщение": warning_message or success_message,
        }
    if passed:
        return {
            "Проверка": name,
            "Статус": "УСПЕХ",
            "Сообщение": success_message,
        }
    return {
        "Проверка": name,
        "Статус": "ОШИБКА",
        "Сообщение": error_message or "Проверка не пройдена.",
    }
