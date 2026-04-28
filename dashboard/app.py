"""Streamlit dashboard for a Russian portfolio demo of Experiment Lab."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import altair as alt
import httpx
import pandas as pd
import streamlit as st

from dashboard.helpers import (
    build_result_summary,
    confidence_interval_text,
    event_label,
    format_metric_value,
    format_money,
    format_number,
    metric_caption,
    metric_label,
    normalize_demo_check,
    relative_lift_text,
    significance_label,
    status_badge_class,
    status_label,
)

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")

GREEN = "#173B2F"
BROWN = "#8B5E34"
SAND = "#F4EFE6"
PAPER = "#FFFDF8"
INK = "#1F2A24"
MUTED = "#68746C"

st.set_page_config(
    page_title="Experiment Lab | A/B тесты",
    page_icon="EL",
    layout="wide",
)


@dataclass(frozen=True)
class ApiResponse:
    """Small API wrapper for safe UI rendering."""

    ok: bool
    data: Any | None = None
    status_code: int | None = None
    error: str | None = None


def apply_theme() -> None:
    """Apply a clean portfolio-oriented visual theme."""
    st.markdown(
        f"""
        <style>
        :root {{
            --green: {GREEN};
            --brown: {BROWN};
            --sand: {SAND};
            --paper: {PAPER};
            --ink: {INK};
            --muted: {MUTED};
            --line: #DED6C8;
            --good: #DDEBE2;
            --warn: #FFF1D7;
            --bad: #F6DFD8;
        }}

        .stApp {{
            background:
                radial-gradient(circle at top left, #E9F0E8 0, transparent 30%),
                linear-gradient(180deg, #FFFDF8 0%, #F5EFE5 100%);
            color: var(--ink);
        }}

        h1, h2, h3 {{
            color: var(--green);
            letter-spacing: -0.02em;
        }}

        p, li, span, div {{
            color: var(--ink);
        }}

        [data-testid="stSidebar"] {{
            background: #EFE7DA;
            border-right: 1px solid var(--line);
        }}

        [data-testid="stSidebar"] * {{
            color: var(--ink);
        }}

        div[data-testid="stMetric"] {{
            background: rgba(255, 253, 248, 0.92);
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 16px 18px;
            box-shadow: 0 10px 28px rgba(31, 42, 36, 0.06);
        }}

        div[data-testid="stMetric"] label {{
            color: var(--muted) !important;
            font-size: 0.92rem !important;
        }}

        div[data-testid="stMetricValue"] {{
            color: var(--green) !important;
            font-weight: 750;
        }}

        div[data-testid="stDataFrame"] {{
            border: 1px solid var(--line);
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 10px 24px rgba(31, 42, 36, 0.04);
        }}

        .hero {{
            background:
                linear-gradient(135deg, rgba(23, 59, 47, 0.98), #315746 62%),
                linear-gradient(45deg, var(--brown), transparent);
            border-radius: 28px;
            padding: 30px 34px;
            margin-bottom: 22px;
            box-shadow: 0 24px 55px rgba(23, 59, 47, 0.22);
        }}

        .hero h1 {{
            color: #FFFDF8;
            margin: 0 0 8px;
            font-size: 44px;
            line-height: 1.05;
        }}

        .hero p {{
            color: #F6EFE4;
            max-width: 860px;
            margin: 0;
            font-size: 17px;
            line-height: 1.55;
        }}

        .flow {{
            display: grid;
            grid-template-columns: repeat(5, minmax(0, 1fr));
            gap: 10px;
            margin: 4px 0 18px;
        }}

        .flow-step {{
            background: rgba(255, 253, 248, 0.86);
            border: 1px solid var(--line);
            border-radius: 16px;
            padding: 13px 14px;
            min-height: 86px;
        }}

        .flow-step b {{
            color: var(--green);
            display: block;
            margin-bottom: 4px;
        }}

        .flow-step span {{
            color: var(--muted);
            font-size: 13px;
        }}

        .badge {{
            display: inline-flex;
            align-items: center;
            border-radius: 999px;
            padding: 6px 11px;
            font-weight: 700;
            font-size: 13px;
            border: 1px solid transparent;
        }}

        .badge-running {{
            background: #DDEBE2;
            color: #173B2F;
            border-color: #AFCBB9;
        }}

        .badge-completed {{
            background: #E8E3D8;
            color: #6F451F;
            border-color: #CAB99F;
        }}

        .badge-draft {{
            background: #F4EFE6;
            color: #68746C;
            border-color: #DED6C8;
        }}

        .badge-paused {{
            background: #FFF1D7;
            color: #755116;
            border-color: #E0C37C;
        }}

        .info-card, .summary-card {{
            background: rgba(255, 253, 248, 0.92);
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 17px 18px;
            margin: 8px 0 12px;
            box-shadow: 0 10px 24px rgba(31, 42, 36, 0.04);
        }}

        .summary-success {{
            border-left: 6px solid var(--green);
            background: #ECF5EE;
        }}

        .summary-neutral, .summary-warning {{
            border-left: 6px solid var(--brown);
            background: #FFF6E8;
        }}

        .summary-danger {{
            border-left: 6px solid #9B3F2E;
            background: #F9E7E1;
        }}

        .muted {{
            color: var(--muted);
            font-size: 14px;
            line-height: 1.45;
        }}

        .check-card {{
            border-radius: 16px;
            padding: 13px 14px;
            border: 1px solid var(--line);
            background: var(--paper);
        }}

        .check-ok {{
            border-left: 6px solid var(--green);
        }}

        .check-warn {{
            border-left: 6px solid var(--brown);
        }}

        .check-error {{
            border-left: 6px solid #9B3F2E;
        }}

        @media (max-width: 900px) {{
            .flow {{
                grid-template-columns: 1fr;
            }}
            .hero h1 {{
                font-size: 34px;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(ttl=20, show_spinner=False)
def api_get(path: str) -> ApiResponse:
    """Fetch JSON from FastAPI without exposing tracebacks to the UI."""
    url = f"{API_BASE_URL}{path}"
    try:
        response = httpx.get(url, timeout=8)
        response.raise_for_status()
        return ApiResponse(
            ok=True,
            data=response.json(),
            status_code=response.status_code,
        )
    except httpx.HTTPStatusError as exc:
        return ApiResponse(
            ok=False,
            status_code=exc.response.status_code,
            error=exc.response.text,
        )
    except httpx.RequestError as exc:
        return ApiResponse(ok=False, error=str(exc))


def rows_to_frame(rows: list[dict[str, Any]] | None) -> pd.DataFrame:
    """Convert API rows to a dataframe."""
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def render_api_down(response: ApiResponse) -> None:
    """Show a friendly API downtime state in Russian."""
    st.error("ОШИБКА: API недоступен.")
    st.markdown(
        f"""
        <div class="info-card">
            <b>Dashboard не смог подключиться к API:</b>
            <code>{API_BASE_URL}</code><br><br>
            Что сделать:
            <ol>
                <li>Запустите <code>docker compose up --build</code>.</li>
                <li>Откройте <code>http://localhost:8000/docs</code>.</li>
                <li>Проверьте эндпоинт <code>GET /health</code>.</li>
                <li>Обновите dashboard кнопкой в боковой панели.</li>
            </ol>
            <span class="muted">Техническая деталь: {response.error or "нет ответа"}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_hero() -> None:
    """Render the top product explanation section."""
    st.markdown(
        """
        <div class="hero">
            <h1>Experiment Lab</h1>
            <p>
                Портфолио-сервис для демонстрации полного цикла A/B теста:
                синтетические события пользователей, запуск эксперимента,
                детерминированное разбиение на контрольную и тестовую группы,
                продуктовых метрик, статистический вывод и бизнес-интерпретация.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_flow() -> None:
    """Explain the product analytics workflow in simple steps."""
    st.markdown("### Как работает проект")
    st.markdown(
        """
        <div class="flow">
            <div class="flow-step">
                <b>1. События</b>
                <span>Пользователи открывают продукт, смотрят товары,
                добавляют в корзину и покупают.</span>
            </div>
            <div class="flow-step">
                <b>2. Эксперимент</b>
                <span>Создается гипотеза, варианты и ключевая метрика.</span>
            </div>
            <div class="flow-step">
                <b>3. Разбиение</b>
                <span>Один и тот же пользователь стабильно попадает в ту же группу.</span>
            </div>
            <div class="flow-step">
                <b>4. Метрики</b>
                <span>API считает конверсию, ARPU, средний чек и частоту покупок.</span>
            </div>
            <div class="flow-step">
                <b>5. Вывод</b>
                <span>Dashboard показывает uplift, p-value, CI и бизнес-решение.</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def event_distribution_chart(events_summary: dict[str, Any]) -> alt.Chart:
    """Build a Russian event distribution chart."""
    frame = rows_to_frame(events_summary.get("by_event_name"))
    frame["Событие"] = frame["event_name"].map(event_label)
    frame = frame.rename(columns={"events_count": "Количество"})

    return (
        alt.Chart(frame)
        .mark_bar(color=GREEN, cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
        .encode(
            x=alt.X("Событие:N", sort="-y", title="Событие"),
            y=alt.Y("Количество:Q", title="Количество событий"),
            tooltip=[
                alt.Tooltip("Событие:N", title="Событие"),
                alt.Tooltip("Количество:Q", title="Количество"),
            ],
        )
        .properties(title="Распределение событий в синтетическом журнале", height=310)
        .configure_title(color=GREEN, fontSize=16, anchor="start")
    )


def assignment_chart(groups: list[dict[str, Any]]) -> alt.Chart:
    """Build a control vs treatment group size chart."""
    frame = rows_to_frame(groups)
    frame["Группа"] = frame["is_control"].map(
        lambda is_control: "Контрольная группа" if is_control else "Тестовая группа"
    )
    frame = frame.rename(columns={"users_count": "Пользователи"})

    return (
        alt.Chart(frame)
        .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
        .encode(
            x=alt.X("Группа:N", title="Группа"),
            y=alt.Y("Пользователи:Q", title="Количество пользователей"),
            color=alt.Color(
                "Группа:N",
                title="Группа",
                scale=alt.Scale(range=[GREEN, BROWN]),
            ),
            tooltip=[
                alt.Tooltip("Группа:N", title="Группа"),
                alt.Tooltip("Пользователи:Q", title="Пользователи"),
            ],
        )
        .properties(title="Размеры контрольной и тестовой групп", height=260)
        .configure_title(color=GREEN, fontSize=16, anchor="start")
    )


def metric_comparison_chart(rows: list[dict[str, Any]]) -> alt.Chart:
    """Build a chart comparing control and treatment metric values."""
    chart_rows: list[dict[str, Any]] = []
    for row in rows:
        metric_name = metric_label(row.get("metric_key"))
        chart_rows.extend(
            [
                {
                    "Метрика": metric_name,
                    "Группа": "Контрольная группа",
                    "Значение": row.get("baseline_value"),
                },
                {
                    "Метрика": metric_name,
                    "Группа": "Тестовая группа",
                    "Значение": row.get("compared_value"),
                },
            ]
        )

    frame = pd.DataFrame(chart_rows)
    return (
        alt.Chart(frame)
        .mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5)
        .encode(
            x=alt.X("Метрика:N", title="Метрика"),
            y=alt.Y("Значение:Q", title="Значение"),
            color=alt.Color(
                "Группа:N",
                title="Группа",
                scale=alt.Scale(range=[GREEN, BROWN]),
            ),
            xOffset="Группа:N",
            tooltip=[
                alt.Tooltip("Метрика:N", title="Метрика"),
                alt.Tooltip("Группа:N", title="Группа"),
                alt.Tooltip("Значение:Q", title="Значение", format=".4f"),
            ],
        )
        .properties(title="Сравнение метрик по группам", height=320)
        .configure_title(color=GREEN, fontSize=16, anchor="start")
    )


def uplift_chart(rows: list[dict[str, Any]]) -> alt.Chart:
    """Build an absolute uplift chart for saved analysis results."""
    frame = rows_to_frame(rows)
    frame["Метрика"] = frame["metric_key"].map(metric_label)
    frame["Абсолютный эффект"] = frame["absolute_lift"]

    return (
        alt.Chart(frame)
        .mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5)
        .encode(
            x=alt.X("Метрика:N", title="Метрика"),
            y=alt.Y("Абсолютный эффект:Q", title="Абсолютный uplift"),
            color=alt.condition(
                alt.datum["Абсолютный эффект"] >= 0,
                alt.value(GREEN),
                alt.value("#9B3F2E"),
            ),
            tooltip=[
                alt.Tooltip("Метрика:N", title="Метрика"),
                alt.Tooltip(
                    "Абсолютный эффект:Q",
                    title="Абсолютный uplift",
                    format=".4f",
                ),
                alt.Tooltip("p_value:Q", title="p-value", format=".4f"),
            ],
        )
        .properties(title="Uplift по сохраненным результатам", height=280)
        .configure_title(color=GREEN, fontSize=16, anchor="start")
    )


def prepare_experiments_frame(experiments: list[dict[str, Any]]) -> pd.DataFrame:
    """Prepare the experiment list with Russian columns."""
    frame = rows_to_frame(experiments)
    if frame.empty:
        return frame
    frame = frame.copy()
    frame["status_label"] = frame["status"].map(status_label)
    return frame.rename(
        columns={
            "id": "ID",
            "experiment_key": "Ключ",
            "name": "Название",
            "status_label": "Статус",
            "start_at": "Старт",
            "end_at": "Окончание",
            "variants_count": "Варианты",
            "assignments_count": "Назначенные пользователи",
        }
    )[
        [
            "ID",
            "Ключ",
            "Название",
            "Статус",
            "Варианты",
            "Назначенные пользователи",
            "Старт",
            "Окончание",
        ]
    ]


def prepare_metrics_frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    """Prepare metric rows with Russian columns and readable formatting."""
    prepared = []
    for row in rows:
        metric_key = str(row.get("metric_key"))
        prepared.append(
            {
                "Метрика": metric_label(metric_key),
                "Что означает": metric_caption(metric_key),
                "Контроль": format_metric_value(metric_key, row.get("baseline_value")),
                "Тестовый вариант": format_metric_value(
                    metric_key,
                    row.get("compared_value"),
                ),
                "Абсолютный эффект": format_number(row.get("absolute_lift")),
                "Относительный эффект": relative_lift_text(row.get("relative_lift")),
                "p-value": format_number(row.get("p_value")),
                "Доверительный интервал": confidence_interval_text(row),
                "Значимо": significance_label(row.get("is_significant")),
                "Тест": row.get("test_method") or "н/д",
            }
        )
    return pd.DataFrame(prepared)


def render_overview(
    users_summary: dict[str, Any],
    events_summary: dict[str, Any],
) -> None:
    """Render the global overview section."""
    st.markdown("## Обзор")
    cols = st.columns(4)
    cols[0].metric("Пользователи", users_summary.get("users_count", 0))
    cols[1].metric("События", events_summary.get("events_count", 0))
    cols[2].metric(
        "Типы событий",
        len(events_summary.get("by_event_name", [])),
        help="Количество разных event_name в журнале событий.",
    )
    cols[3].metric("Выручка", format_money(events_summary.get("revenue_total", 0)))

    st.markdown(
        """
        <div class="info-card">
            <b>Что показывает журнал событий:</b>
            это синтетическая e-commerce / product app история поведения
            пользователей. В ней есть верх воронки, добавления в корзину,
            покупки и подписочные события. Эти данные потом соединяются с
            assignment-таблицей, чтобы считать метрики по группам эксперимента.
        </div>
        """,
        unsafe_allow_html=True,
    )

    if events_summary.get("by_event_name"):
        st.altair_chart(event_distribution_chart(events_summary), use_container_width=True)
    else:
        st.info("События пока не загружены. Запустите seed или ingestion pipeline.")


def render_experiments(experiments: list[dict[str, Any]]) -> None:
    """Render the experiment list section."""
    st.markdown("## Эксперименты")
    if not experiments:
        st.info(
            "Экспериментов пока нет. Создайте эксперимент через "
            "POST /experiments, затем назначьте пользователей через "
            "POST /experiments/{key}/start."
        )
        return

    st.dataframe(
        prepare_experiments_frame(experiments),
        use_container_width=True,
        hide_index=True,
    )
    st.caption(
        "Статусы переведены для демо: Черновик, Запущен, Завершен, "
        "Приостановлен. Колонка назначений показывает, есть ли пользователи "
        "в контрольной и тестовой группах."
    )


def render_experiment_header(experiment: dict[str, Any]) -> None:
    """Render selected experiment metadata."""
    badge = status_badge_class(experiment.get("status"))
    st.markdown("## Выбранный эксперимент")
    st.markdown(
        f"""
        <div class="info-card">
            <h3 style="margin-top:0">{experiment.get("name", "Без названия")}</h3>
            <span class="badge {badge}">{status_label(experiment.get("status"))}</span>
            <p class="muted" style="margin-top:12px">
                <b>Ключ:</b> {experiment.get("experiment_key", "н/д")} ·
                <b>Владелец:</b> {experiment.get("owner_name") or "н/д"} ·
                <b>Основная метрика:</b>
                {metric_label(experiment.get("primary_metric_key"))}
            </p>
            <p><b>Гипотеза:</b> {experiment.get("hypothesis") or "Не указана"}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_assignments(assignments: dict[str, Any]) -> None:
    """Render assignment group sizes."""
    st.markdown("### Разбиение пользователей")
    groups = assignments.get("groups", [])
    if not groups:
        st.info(
            "Назначений пока нет. Запустите "
            "POST /experiments/{key}/start, чтобы распределить пользователей."
        )
        return

    cols = st.columns(len(groups))
    for column, group in zip(cols, groups, strict=False):
        label = "Контроль" if group.get("is_control") else "Тестовый вариант"
        column.metric(label, group.get("users_count", 0))

    st.altair_chart(assignment_chart(groups), use_container_width=True)


def render_metrics(metrics: dict[str, Any] | None) -> None:
    """Render live metrics section."""
    st.markdown("## Метрики")
    st.markdown(
        """
        <div class="info-card">
            <b>Текущие метрики</b> считаются на лету из текущих событий и
            назначений пользователей. Это удобно для мониторинга, но такие
            результаты не сохраняются в таблицу experiment_results.
        </div>
        """,
        unsafe_allow_html=True,
    )

    rows = [] if not metrics else metrics.get("results", [])
    if not rows:
        st.info(
            "Текущие метрики пока недоступны. Обычно это значит, что у "
            "эксперимента еще нет назначенных пользователей."
        )
        return

    st.dataframe(prepare_metrics_frame(rows), use_container_width=True, hide_index=True)
    st.altair_chart(metric_comparison_chart(rows), use_container_width=True)


def render_saved_results(results: dict[str, Any] | None, experiment_key: str) -> None:
    """Render saved statistical analysis and final interpretation."""
    st.markdown("## Статистические результаты")
    st.markdown(
        """
        <div class="info-card">
            <b>Сохраненные результаты</b> появляются после запуска анализа
            через API. Здесь уже есть
            uplift, p-value, доверительные интервалы и флаг значимости.
        </div>
        """,
        unsafe_allow_html=True,
    )

    rows = [] if not results else results.get("results", [])
    if not rows:
        st.warning(
            "Сохраненных результатов анализа пока нет. "
            f"Вызовите POST /experiments/{experiment_key}/analyze через "
            "документацию FastAPI или curl."
        )
    else:
        st.dataframe(prepare_metrics_frame(rows), use_container_width=True, hide_index=True)
        st.altair_chart(uplift_chart(rows), use_container_width=True)

    summary, tone = build_result_summary(rows)
    st.markdown(
        f"""
        <div class="summary-card summary-{tone}">
            <b>Итоговая интерпретация A/B теста</b><br>
            {summary}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_demo_checks(
    selected_experiment_id: int | None,
    cached: dict[str, ApiResponse],
) -> None:
    """Render demo smoke checks without crashing on partial failures."""
    st.markdown("## Проверка демо")
    st.caption(
        "Этот блок нужен для защиты проекта: он быстро показывает, какие "
        "части API и dashboard сейчас работают."
    )

    checks: list[dict[str, str]] = []
    health = cached.get("health") or api_get("/health")
    users = cached.get("users") or api_get("/users/summary")
    events = cached.get("events") or api_get("/events/summary")
    experiments = cached.get("experiments") or api_get("/experiments")

    checks.append(
        normalize_demo_check(
            "Проверка доступности API",
            health.ok and health.data and health.data.get("status") == "ok",
            "УСПЕХ: API доступен",
            error_message="ОШИБКА: API недоступен",
        )
    )
    checks.append(
        normalize_demo_check(
            "Сводка пользователей",
            users.ok and users.data and users.data.get("users_count", 0) > 0,
            "УСПЕХ: данные пользователей загружены",
            error_message="ОШИБКА: пользователи не загружены",
        )
    )
    checks.append(
        normalize_demo_check(
            "Сводка событий",
            events.ok and events.data and events.data.get("events_count", 0) > 0,
            "УСПЕХ: события загружены",
            error_message="ОШИБКА: события не загружены",
        )
    )
    checks.append(
        normalize_demo_check(
            "Список экспериментов",
            experiments.ok and bool(experiments.data),
            "УСПЕХ: список экспериментов загружен",
            error_message="ОШИБКА: эксперименты не найдены или API вернул ошибку",
        )
    )

    if selected_experiment_id is None:
        checks.append(
            normalize_demo_check(
                "Выбранный эксперимент",
                False,
                "",
                warning=True,
                warning_message="ПРЕДУПРЕЖДЕНИЕ: эксперимент не выбран",
            )
        )
    else:
        detail = cached.get("detail") or api_get(f"/experiments/{selected_experiment_id}")
        assignments = cached.get("assignments") or api_get(
            f"/experiments/{selected_experiment_id}/assignments"
        )
        metrics = cached.get("metrics") or api_get(
            f"/experiments/{selected_experiment_id}/metrics"
        )
        results = cached.get("results") or api_get(
            f"/experiments/{selected_experiment_id}/results"
        )

        checks.extend(
            [
                normalize_demo_check(
                    "Детали эксперимента",
                    detail.ok and bool(detail.data),
                    "УСПЕХ: детали эксперимента загружены",
                    error_message="ОШИБКА: детали эксперимента недоступны",
                ),
                normalize_demo_check(
                    "Назначения пользователей",
                    assignments.ok
                    and assignments.data
                    and assignments.data.get("total_assigned", 0) > 0,
                    "УСПЕХ: назначения пользователей загружены",
                    error_message="ОШИБКА: назначения не загружены",
                ),
                normalize_demo_check(
                    "Расчет метрик",
                    metrics.ok and metrics.data and bool(metrics.data.get("results")),
                    "УСПЕХ: текущие метрики рассчитаны",
                    error_message="ОШИБКА: текущие метрики недоступны",
                ),
                normalize_demo_check(
                    "Сохраненные результаты",
                    results.ok,
                    "УСПЕХ: эндпоинт сохраненных результатов доступен",
                    warning=results.ok
                    and not bool((results.data or {}).get("results", [])),
                    warning_message=(
                        "ПРЕДУПРЕЖДЕНИЕ: сохраненных результатов анализа пока нет"
                    ),
                    error_message="ОШИБКА: эндпоинт результатов недоступен",
                ),
            ]
        )

    for check in checks:
        status = check["Статус"]
        css_class = {
            "УСПЕХ": "check-ok",
            "ПРЕДУПРЕЖДЕНИЕ": "check-warn",
            "ОШИБКА": "check-error",
        }.get(status, "check-warn")
        st.markdown(
            f"""
            <div class="check-card {css_class}">
                <b>{check["Проверка"]}</b><br>
                {check["Сообщение"]}
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_sidebar(
    health: ApiResponse,
    experiments: list[dict[str, Any]],
) -> int | None:
    """Render sidebar navigation and return selected experiment id."""
    selected_id: int | None = None
    with st.sidebar:
        st.title("Навигация")
        st.caption(f"API: {API_BASE_URL}")

        if health.ok:
            st.success("УСПЕХ: API доступен")
        else:
            st.error("ОШИБКА: API недоступен")

        if st.button("Обновить данные", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.divider()
        st.subheader("Эксперимент")
        if experiments:
            options = {
                (
                    f"{item['experiment_key']} · "
                    f"{status_label(item.get('status'))}"
                ): item["id"]
                for item in experiments
            }
            selected = st.selectbox(
                "Выберите эксперимент",
                options=list(options.keys()),
            )
            selected_id = options[selected]
        else:
            st.info("Экспериментов пока нет.")

        st.divider()
        st.subheader("Что показывать")
        st.caption(
            "1. Обзор событий и пользователей.\n\n"
            "2. Список экспериментов и статусы.\n\n"
            "3. Разбиение на контрольную и тестовую группы.\n\n"
            "4. Метрики, uplift и статистический вывод.\n\n"
            "5. Блок «Проверка демо»."
        )

    return selected_id


def main() -> None:
    """Render the dashboard application."""
    apply_theme()

    health = api_get("/health")
    experiments_response = api_get("/experiments") if health.ok else ApiResponse(ok=False)
    experiments = experiments_response.data if experiments_response.ok else []
    selected_id = render_sidebar(health, experiments)

    render_hero()
    render_flow()

    if not health.ok:
        render_api_down(health)
        render_demo_checks(None, {"health": health})
        return

    users_response = api_get("/users/summary")
    events_response = api_get("/events/summary")
    cached: dict[str, ApiResponse] = {
        "health": health,
        "experiments": experiments_response,
        "users": users_response,
        "events": events_response,
    }

    if users_response.ok and events_response.ok:
        render_overview(users_response.data, events_response.data)
    else:
        st.warning(
            "Сводки пользователей или событий пока недоступны. Проверьте, "
            "что PostgreSQL и seed/ingestion данные запущены."
        )

    st.divider()
    render_experiments(experiments)

    if selected_id is None:
        st.divider()
        render_demo_checks(None, cached)
        return

    detail = api_get(f"/experiments/{selected_id}")
    assignments = api_get(f"/experiments/{selected_id}/assignments")
    metrics = api_get(f"/experiments/{selected_id}/metrics")
    results = api_get(f"/experiments/{selected_id}/results")
    cached.update(
        {
            "detail": detail,
            "assignments": assignments,
            "metrics": metrics,
            "results": results,
        }
    )

    st.divider()
    if detail.ok and detail.data:
        render_experiment_header(detail.data)
    else:
        st.error("ОШИБКА: детали выбранного эксперимента недоступны.")

    if assignments.ok and assignments.data:
        render_assignments(assignments.data)
    else:
        st.warning("Назначения для выбранного эксперимента недоступны.")

    st.divider()
    render_metrics(metrics.data if metrics.ok else None)

    st.divider()
    experiment_key = detail.data.get("experiment_key", "key") if detail.data else "key"
    render_saved_results(results.data if results.ok else None, experiment_key)

    st.divider()
    render_demo_checks(selected_id, cached)


if __name__ == "__main__":
    main()
