"""Minimal Streamlit dashboard for the Experiment Lab project."""

import streamlit as st

st.set_page_config(page_title="Experiment Lab", page_icon="🧪", layout="wide")

st.title("Experiment Lab")
st.caption("Portfolio scaffold for product experiments and A/B test analysis.")

st.subheader("Current stage")
st.write(
    "Stage 1 focuses on project packaging: API, dashboard, database container, "
    "tests, and developer tooling."
)

st.subheader("Planned modules")
st.write(
    "- Event storage\n"
    "- Experiment setup\n"
    "- User split logic\n"
    "- Metric calculation\n"
    "- A/B test analysis\n"
    "- Result dashboards"
)
