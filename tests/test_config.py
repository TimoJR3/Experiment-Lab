"""Configuration tests for the project scaffold."""

from app.core.config import settings


def test_database_url_contains_postgres_driver() -> None:
    """Database URL should be assembled from application settings."""
    assert settings.database_url.startswith("postgresql+psycopg://")
