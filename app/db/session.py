"""Database connection helpers used by initialization and future data access."""

from app.core.config import settings


def get_raw_database_url() -> str:
    """Build a psycopg-compatible PostgreSQL connection URL."""
    return (
        "postgresql://"
        f"{settings.postgres_user}:{settings.postgres_password}"
        f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
    )


def get_database_url() -> str:
    """Expose the SQLAlchemy-style database URL for future integrations."""
    return settings.database_url
