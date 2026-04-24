"""Streamlit dashboard for browsing experiments and analysis results."""

from __future__ import annotations

import os
from typing import Any

import httpx
import pandas as pd
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")


st.set_page_config(page_title="Experiment Lab", page_icon=":bar_chart:", layout="wide")


def api_get(path: str) -> Any:
    """Load JSON from the FastAPI backend with basic error handling."""
    try:
        response = httpx.get(f"{API_BASE_URL}{path}", timeout=10)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text
        st.error(f"API returned {exc.response.status_code}: {detail}")
    except httpx.RequestError as exc:
        st.error(f"Cannot connect to API at {API_BASE_URL}: {exc}")
    return None


def to_frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    """Convert API rows to a display-friendly dataframe."""
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def format_percent(value: float | None) -> str:
    """Format a decimal value as percent text."""
    if value is None:
        return "n/a"
    return f"{value * 100:.2f}%"


def format_number(value: float | None) -> str:
    """Format numeric metric values compactly."""
    if value is None:
        return "n/a"
    return f"{value:.4f}"


def build_effect_summary(results: list[dict[str, Any]]) -> str:
    """Build a short human-readable summary for the selected experiment."""
    if not results:
        return "No saved results yet. Run analysis first to get statistical conclusions."

    significant = [row for row in results if row.get("is_significant") is True]
    if not significant:
        return (
            "No statistically significant effect was detected at alpha = 0.05. "
            "Treat observed uplift as directional until more data is collected."
        )

    best = max(significant, key=lambda row: abs(row.get("absolute_lift") or 0))
    direction = "positive" if (best.get("absolute_lift") or 0) > 0 else "negative"
    return (
        f"Detected a {direction} statistically significant effect for "
        f"{best['metric_key']} with absolute lift {best['absolute_lift']:.4f} "
        f"and p-value {best['p_value']:.4f}."
    )


def render_overview() -> None:
    """Render global data summaries."""
    users_summary = api_get("/users/summary")
    events_summary = api_get("/events/summary")

    if not users_summary or not events_summary:
        return

    left, middle, right, revenue = st.columns(4)
    left.metric("Users", users_summary["users_count"])
    middle.metric("Events", events_summary["events_count"])
    right.metric("Event types", len(events_summary["by_event_name"]))
    revenue.metric("Revenue", f"${events_summary['revenue_total']:.2f}")

    st.subheader("Event mix")
    event_frame = to_frame(events_summary["by_event_name"])
    if not event_frame.empty:
        st.bar_chart(event_frame.set_index("event_name")["events_count"])


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
    meta_cols[0].metric("Status", experiment["status"])
    meta_cols[1].metric("Assigned users", assignments["total_assigned"])
    meta_cols[2].metric("Experiment key", experiment["experiment_key"])
    meta_cols[3].metric("Owner", experiment.get("owner_name") or "n/a")

    if experiment.get("hypothesis"):
        st.caption(f"Hypothesis: {experiment['hypothesis']}")

    tabs = st.tabs(["Assignments", "Live metrics", "Saved results", "Summary"])

    with tabs[0]:
        group_frame = to_frame(assignments["groups"])
        if group_frame.empty:
            st.info("No assignments found for this experiment.")
        else:
            st.dataframe(group_frame, use_container_width=True, hide_index=True)

    with tabs[1]:
        live_rows = [] if not metrics else metrics["results"]
        live_frame = to_frame(live_rows)
        if live_frame.empty:
            st.info("Live metrics are unavailable until the experiment has assignments.")
        else:
            st.dataframe(
                live_frame[
                    [
                        "metric_key",
                        "baseline_value",
                        "compared_value",
                        "absolute_lift",
                        "relative_lift",
                        "p_value",
                        "test_method",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
            )

    with tabs[2]:
        result_rows = [] if not saved_results else saved_results["results"]
        result_frame = to_frame(result_rows)
        if result_frame.empty:
            st.info("No saved analysis results yet. Call the analyze endpoint first.")
        else:
            st.dataframe(
                result_frame[
                    [
                        "metric_key",
                        "baseline_value",
                        "compared_value",
                        "absolute_lift",
                        "relative_lift",
                        "p_value",
                        "ci_lower",
                        "ci_upper",
                        "is_significant",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
            )

    with tabs[3]:
        result_rows = [] if not saved_results else saved_results["results"]
        st.write(build_effect_summary(result_rows))
        st.caption(
            "Live metrics are calculated from current assignments and events. "
            "Saved results come from experiment_results after running analysis."
        )


def main() -> None:
    """Render the dashboard application."""
    st.title("Experiment Lab")
    st.caption("MVP dashboard for product experiments, assignments, metrics, and results.")

    experiments = api_get("/experiments")
    if experiments is None:
        return

    render_overview()

    st.divider()
    st.subheader("Experiments")

    if not experiments:
        st.info("No experiments found. Create and start an experiment through the API first.")
        return

    experiments_frame = to_frame(experiments)
    st.dataframe(experiments_frame, use_container_width=True, hide_index=True)

    options = {
        f"{row['id']} | {row['experiment_key']} | {row['status']}": row["id"]
        for row in experiments
    }
    selected_label = st.selectbox("Select experiment", options=list(options))
    render_experiment_details(options[selected_label])


if __name__ == "__main__":
    main()
