"""Tests for the reproducible demo setup module."""

from pathlib import Path

from app.db import prepare_demo

BASE_DIR = Path(__file__).resolve().parents[1]


def test_prepare_demo_module_can_be_imported() -> None:
    """The demo setup module should be importable without DB side effects."""
    assert prepare_demo.DEMO_USERS_COUNT == 10_000


def test_demo_experiment_key_is_consistent() -> None:
    """The public demo experiment key should stay stable for docs and UI."""
    assert prepare_demo.DEMO_EXPERIMENT_KEY == "big_data_checkout_test"


def test_readme_mentions_demo_command() -> None:
    """README should include the one-command demo preparation flow."""
    readme = (BASE_DIR / "README.md").read_text(encoding="utf-8")

    assert "docker compose exec api python -m app.db.prepare_demo" in readme
    assert "big_data_checkout_test" in readme
    assert "http://localhost:8501" in readme
    assert "http://localhost:8000/docs" in readme


def test_docs_do_not_reference_missing_demo_key() -> None:
    """Demo documentation should reference the real reproducible experiment."""
    docs = [
        BASE_DIR / "README.md",
        BASE_DIR / "docs" / "demo_checklist.md",
    ]

    for path in docs:
        text = path.read_text(encoding="utf-8")
        assert prepare_demo.DEMO_EXPERIMENT_KEY in text
