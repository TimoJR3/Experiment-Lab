"""Application settings loaded from environment variables."""

from dataclasses import dataclass
import os

from dotenv import load_dotenv

load_dotenv()


@dataclass(slots=True)
class Settings:
    """Typed configuration for local development."""

    app_name: str = os.getenv("APP_NAME", "Experiment Lab")
    app_env: str = os.getenv("APP_ENV", "local")
    postgres_host: str = os.getenv("POSTGRES_HOST", "localhost")
    postgres_port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    postgres_db: str = os.getenv("POSTGRES_DB", "experiment_lab")
    postgres_user: str = os.getenv("POSTGRES_USER", "experiment_user")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "experiment_password")

    @property
    def database_url(self) -> str:
        """Build PostgreSQL connection URL for future DB integration."""
        return (
            "postgresql+psycopg://"
            f"{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
