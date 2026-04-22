"""Utilities for applying PostgreSQL schema and seed SQL files."""

from __future__ import annotations

import argparse
from pathlib import Path

import psycopg

from app.db.session import get_raw_database_url

BASE_DIR = Path(__file__).resolve().parents[2]
SQL_DIR = BASE_DIR / "sql"
SCHEMA_FILE = SQL_DIR / "001_init_schema.sql"
SEED_FILE = SQL_DIR / "002_seed_data.sql"


def execute_sql_file(file_path: Path) -> None:
    """Execute a SQL script against the configured PostgreSQL database."""
    sql = file_path.read_text(encoding="utf-8")

    with psycopg.connect(get_raw_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql)
        connection.commit()


def parse_args() -> argparse.Namespace:
    """Parse CLI flags for schema and seed initialization."""
    parser = argparse.ArgumentParser(description="Initialize Experiment Lab database.")
    parser.add_argument(
        "--schema",
        action="store_true",
        help="Apply the PostgreSQL schema.",
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Load demo seed data.",
    )
    return parser.parse_args()


def main() -> None:
    """Run the requested initialization steps."""
    args = parse_args()

    if not args.schema and not args.seed:
        msg = "Pass --schema, --seed, or both."
        raise SystemExit(msg)

    if args.schema:
        execute_sql_file(SCHEMA_FILE)
        print(f"Applied schema: {SCHEMA_FILE}")

    if args.seed:
        execute_sql_file(SEED_FILE)
        print(f"Applied seed: {SEED_FILE}")


if __name__ == "__main__":
    main()
