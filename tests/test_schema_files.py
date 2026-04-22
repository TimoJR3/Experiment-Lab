"""Sanity checks for SQL schema and seed files."""

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]


def test_schema_contains_required_tables() -> None:
    """Schema file should declare all required data model tables."""
    schema_sql = (BASE_DIR / "sql" / "001_init_schema.sql").read_text(encoding="utf-8")

    required_tables = [
        "users",
        "events",
        "experiments",
        "experiment_variants",
        "experiment_assignments",
        "metrics_definitions",
        "experiment_results",
    ]

    for table_name in required_tables:
        assert f"CREATE TABLE IF NOT EXISTS {table_name}" in schema_sql


def test_seed_contains_demo_experiment() -> None:
    """Seed file should load a demo experiment for local development."""
    seed_sql = (BASE_DIR / "sql" / "002_seed_data.sql").read_text(encoding="utf-8")

    assert "checkout_button_v1" in seed_sql
    assert "purchase_conversion" in seed_sql
