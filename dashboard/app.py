"""Streamlit dashboard for browsing experiments and analysis results."""

from __future__ import annotations

import os
from typing import Any

import altair as alt
import httpx
import pandas as pd
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")

STATUS_LABELS = {
    "draft": "Черновик",
    "running": "Запущен",
    "completed": "Завершен",
}

METRIC_LABELS = {
    "conversion_rate": "Конверсия",
    "average_revenue_per_user": "ARPU",
    "average_order_value": "Средний чек",
    "purchase_rate": "Покупки на пользователя",
}


st.set_page_config(page_title="Experiment Lab", page_icon="EL", layout="wide")


def apply_theme() -> None:
    """Apply a minimal brown and dark-green visual theme."""
    st.markdown(
        """
        <style>
        :root {
            --green: #183A2D;
            --green-soft: #E8F0EA;
            --brown: #8B5E34;
            --brown-soft: #F3ECE3;
            --ink: #1F2521;
            --muted: #667069;
            --line: #D9DDD6;
            --paper: #FBFAF7;
        }

        .stApp {
            background: linear-gradient(180deg, #FBFAF7 0%, #F5F1EA 100%);
            color: var(--ink);
        }

        h1, h2, h3 {
            color: var(--green);
            letter-spacing: 0;
        }

        [data-testid="stSidebar"] {
            background: #EFE7DC;
            border-right: 1px solid var(--line);
        }

        [data-testid="stMetric"] {
            background: rgba(255, 255, 255, 0.72);
            border: 1px solid var(--line);
            border-left: 4px solid var(--green);
            padding: 14px 16px;
            border-radius: 8px;
        }

        div[data-testid="stDataFrame"] {
            border: 1px solid var(--line);
            border-radius: 8px;
            overflow: hidden;
        }

        .hero {
            background: linear-gradient(135deg, #183A2D 0%, #2F4A3F 62%, #8B5E34 100%);
            color: white;
            padding: 24px 28px;
            border-radius: 8px;
            margin-bottom: 18px;
        }

        .hero h1 {
            color: white;
            margin: 0 0 6px 0;
            font-size: 34px;
            line-height: 1.1;
        }

        .hero p {
            color: #F6F1E9;
            margin: 0;
            font-size: 16px;
        }

        .note {
            background: var(--brown-soft);
            border-left: 4px solid var(--brown);
            padding: 13px 15px;
            border-radius: 8px;
            color: var(--ink);
        }

        .summary-good {
            background: var(--green-soft);
            border-left: 4px solid var(--green);
            padding: 14px 16px;
            border-radius: 8px;
            color: var(--ink);
        }

        .summary-neutral {
            background: #FFF7E8;
            border-left: 4px solid var(--brown);
            padding: 14px 16px;
            border-radius: 8px;
            color: var(--ink);
        }

        .small-muted {
            color: var(--muted);
            font-size: 13px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def api_get(path: str) -> Any:
    """Load JSON from the FastAPI backend with basic error handling."""
    try:
        response = httpx.get(f"{API_BASE_URL}{path}", timeout=10)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as exc:
        st.error(f"API вернул ошибку {exc.response.status_code}: {exc.response.text}")
    except httpx.RequestError as exc:
        st.error(f"Не удалось подключиться к API `{API_BASE_URL}`: {exc}")
    return None


def to_frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    """Convert API rows to a dataframe."""
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def status_label(status: str | None) -> str:
    """Translate experiment status to Russian."""
    if not status:
        return "Неизвестно"
    return STATUS_LABELS.get(status, status)


def metric_label(metric_key: str) -> str:
    """Translate metric key to Russian."""
    return METRIC_LABELS.get(metric_key, metric_key)


def format_ratio(value: float | None) -> str:
    """Format a ratio as a compact percentage."""
    if value is None:
        return "н/д"
    return f"{value * 100:.2f}%"


def format_number(value: float | None) -> str:
    """Format a numeric value."""
    if value is None:
        return "н/д"
    return f"{value:.4f}"


def build_effect_summary(results: list[dict[str, Any]]) -> tuple[str, bool]:
    """Build a short Russian summary for saved analysis results."""
    if not results:
        return (
            "Сохраненных результатов пока нет. Запустите анализ через API, чтобы увидеть статистический вывод.",
            False,
        )

    significant = [row for row in results if row.get("is_significant") is True]
    if not significant:
        return (
            "Статистически значимого эффекта на уровне alpha = 0.05 не найдено. "
            "Наблюдаемый uplift можно рассматривать как направление, но не как надежное доказательство эффекта.",
            False,
        )

    best = max(significant, key=lambda row: abs(row.get("absolute_lift") or 0))
    direction = "положительный" if (best.get("absolute_lift") or 0) > 0 else "отрицательный"
    metric_name = metric_label(str(best["metric_key"]))
    return (
        f"Обнаружен {direction} статистически значимый эффект по метрике «{metric_name}»: "
        f"absolute lift = {best['absolute_lift']:.4f}, p-value = {best['p_value']:.4f}.",
        True,
    )


def prepare_experiment_frame(experiments: list[dict[str, Any]]) -> pd.DataFrame:
    """Prepare experiment list for display."""
    frame = to_frame(experiments)
    if frame.empty:
        return frame
    frame = frame.copy()
    frame["status"] = frame["status"].map(status_label)
    return frame.rename(
        columns={
            "id": "ID",
            "experiment_key": "Ключ",
            "name": "Название",
            "status": "Статус",
            "start_at": "Старт",
            "end_at": "Окончание",
            "variants_count": "Варианты",
            "assignments_count": "Участники",
        }
    )


def prepare_groups_frame(groups: list[dict[str, Any]]) -> pd.DataFrame:
    """Prepare assignment groups for display."""
    frame = to_frame(groups)
    if frame.empty:
        return frame
    frame = frame.copy()
    frame["is_control"] = frame["is_control"].map(lambda value: "control" if value else "treatment")
    return frame.rename(
        columns={
            "variant_id": "ID варианта",
            "variant_key": "Вариант",
            "is_control": "Тип",
            "users_count": "Пользователи",
        }
    )


def prepare_metrics_frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    """Prepare metrics for display."""
    frame = to_frame(rows)
    if frame.empty:
        return frame
    frame = frame.copy()
    frame["metric_key"] = frame["metric_key"].map(metric_label)
    for column in ["baseline_value", "compared_value", "absolute_lift", "relative_lift", "p_value", "ci_lower", "ci_upper"]:
        if column in frame.columns:
            frame[column] = frame[column].map(format_number)
    if "is_significant" in frame.columns:
        frame["is_significant"] = frame["is_significant"].map(
            lambda value: "да" if value is True else "нет" if value is False else "н/д"
        )
    return frame.rename(
        columns={
            "metric_key": "Метрика",
            "baseline_value": "Контроль",
            "compared_value": "Тестовая группа",
            "absolute_lift": "Абс. эффект",
            "relative_lift": "Отн. эффект",
            "p_value": "p-value",
            "ci_lower": "CI ниж.",
            "ci_upper": "CI верх.",
            "is_significant": "Значимо",
            "test_method": "Тест",
        }
    )


def render_event_chart(events_summary: dict[str, Any]) -> None:
    """Render event mix chart with project palette."""
    event_frame = to_frame(events_summary["by_event_name"])
    if event_frame.empty:
        st.info("События пока не загружены.")
        return

    chart = (
        alt.Chart(event_frame)
        .mark_bar(color="#183A2D", cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
        .encode(
            x=alt.X("event_name:N", title="Событие", sort="-y"),
            y=alt.Y("events_count:Q", title="Количество"),
            tooltip=[
                alt.Tooltip("event_name:N", title="Событие"),
                alt.Tooltip("events_count:Q", title="Количество"),
            ],
        )
        .properties(height=260)
    )
    st.altair_chart(chart, use_container_width=True)


def render_overview() -> None:
    """Render global users and events summaries."""
    users_summary = api_get("/users/summary")
    events_summary = api_get("/events/summary")

    if not users_summary or not events_summary:
        return

    st.subheader("Обзор данных")
    left, middle, right, revenue = st.columns(4)
    left.metric("Пользователи", users_summary["users_count"])
    middle.metric("События", events_summary["events_count"])
    right.metric("Типы событий", len(events_summary["by_event_name"]))
    revenue.metric("Выручка", f"${events_summary['revenue_total']:.2f}")

    st.markdown('<div class="small-muted">Распределение событий в загруженном event log</div>', unsafe_allow_html=True)
    render_event_chart(events_summary)


def render_experiment_details(experiment_id: int) -> None:
    """Render selected experiment details and analysis sections."""
    experiment = api_get(f"/experiments/{experiment_id}")
    assignments = api_get(f"/experiments/{experiment_id}/assignments")
    metrics = api_get(f"/experiments/{experiment_id}/metrics")
    saved_results = api_get(f"/experiments/{experiment_id}/results")

    if not experiment or not assignments:
        return

    st.subheader(experiment["name"])
    meta_cols = st.columns(4)
    meta_cols[0].metric("Статус", status_label(experiment["status"]))
    meta_cols[1].metric("Участники", assignments["total_assigned"])
    meta_cols[2].metric("Ключ", experiment["experiment_key"])
    meta_cols[3].metric("Владелец", experiment.get("owner_name") or "н/д")

    if experiment.get("hypothesis"):
        st.markdown(f'<div class="note"><b>Гипотеза:</b> {experiment["hypothesis"]}</div>', unsafe_allow_html=True)

    tabs = st.tabs(["Группы", "Текущие метрики", "Сохраненные результаты", "Вывод"])

    with tabs[0]:
        group_frame = prepare_groups_frame(assignments["groups"])
        if group_frame.empty:
            st.info("Для этого эксперимента пока нет назначений.")
        else:
            st.dataframe(group_frame, use_container_width=True, hide_index=True)

    with tabs[1]:
        live_rows = [] if not metrics else metrics["results"]
        live_frame = prepare_metrics_frame(live_rows)
        if live_frame.empty:
            st.info("Live-метрики появятся после назначения пользователей в эксперимент.")
        else:
            columns = ["Метрика", "Контроль", "Тестовая группа", "Абс. эффект", "Отн. эффект", "p-value", "Тест"]
            st.dataframe(live_frame[columns], use_container_width=True, hide_index=True)

    with tabs[2]:
        result_rows = [] if not saved_results else saved_results["results"]
        result_frame = prepare_metrics_frame(result_rows)
        if result_frame.empty:
            st.info("Сохраненных результатов пока нет. Запустите `POST /experiments/{experiment_key}/analyze`.")
        else:
            columns = [
                "Метрика",
                "Контроль",
                "Тестовая группа",
                "Абс. эффект",
                "Отн. эффект",
                "p-value",
                "CI ниж.",
                "CI верх.",
                "Значимо",
            ]
            st.dataframe(result_frame[columns], use_container_width=True, hide_index=True)

    with tabs[3]:
        result_rows = [] if not saved_results else saved_results["results"]
        summary, is_positive = build_effect_summary(result_rows)
        css_class = "summary-good" if is_positive else "summary-neutral"
        st.markdown(f'<div class="{css_class}">{summary}</div>', unsafe_allow_html=True)
        st.caption(
            "Текущие метрики считаются на лету из назначений пользователей и событий. "
            "Сохраненные результаты берутся из experiment_results после запуска анализа."
        )


def main() -> None:
    """Render the dashboard application."""
    apply_theme()

    st.markdown(
        """
        <div class="hero">
            <h1>Experiment Lab</h1>
            <p>Понятный dashboard для A/B экспериментов: группы, метрики, uplift и статистический вывод.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.header("Навигация")
        st.caption(f"API: {API_BASE_URL}")
        if st.button("Обновить данные", use_container_width=True):
            st.rerun()

    experiments = api_get("/experiments")
    if experiments is None:
        return

    render_overview()

    st.divider()
    st.subheader("Эксперименты")

    if not experiments:
        st.info("Эксперименты пока не найдены. Создайте и запустите эксперимент через API.")
        return

    experiments_frame = prepare_experiment_frame(experiments)
    st.dataframe(experiments_frame, use_container_width=True, hide_index=True)

    options = {
        f"{row['id']} | {row['experiment_key']} | {status_label(row['status'])}": row["id"]
        for row in experiments
    }
    with st.sidebar:
        selected_label = st.selectbox("Выберите эксперимент", options=list(options))

    render_experiment_details(options[selected_label])


if __name__ == "__main__":
    main()
