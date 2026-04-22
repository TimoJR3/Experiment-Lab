"""Database connection settings placeholder for later stages."""

from app.core.config import settings


def get_database_url() -> str:
    """Expose the database URL in one place for future integrations."""
    return settings.database_url
