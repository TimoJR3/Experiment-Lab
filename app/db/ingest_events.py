"""Generate synthetic users and events, validate them, and load them into PostgreSQL."""

from __future__ import annotations

import argparse
from collections.abc import Iterable
from decimal import Decimal

from psycopg.types.json import Json

from app.db.session import get_db_connection
from app.experiments.synthetic_data import GenerationConfig, SyntheticDataset, generate_dataset
from app.schemas.events import EventIngestionRecord, UserIngestionRecord


USER_UPSERT_SQL = """
INSERT INTO users (
    user_key,
    registered_at,
    country_code,
    device_type,
    acquisition_channel,
    attributes
)
VALUES (
    %(user_key)s,
    %(registered_at)s,
    %(country_code)s,
    %(device_type)s,
    %(acquisition_channel)s,
    %(attributes)s
)
ON CONFLICT (user_key) DO UPDATE
SET
    registered_at = EXCLUDED.registered_at,
    country_code = EXCLUDED.country_code,
    device_type = EXCLUDED.device_type,
    acquisition_channel = EXCLUDED.acquisition_channel,
    attributes = EXCLUDED.attributes;
"""

EVENT_INSERT_SQL = """
INSERT INTO events (
    event_uuid,
    user_id,
    event_name,
    event_timestamp,
    event_value,
    event_properties
)
VALUES (
    %(event_uuid)s,
    %(user_id)s,
    %(event_name)s,
    %(event_timestamp)s,
    %(event_value)s,
    %(event_properties)s
)
ON CONFLICT (event_uuid) DO NOTHING;
"""


def _serialize_users(users: Iterable[UserIngestionRecord]) -> list[dict]:
    """Prepare user rows for psycopg insertion."""
    return [
        {
            "user_key": user.user_key,
            "registered_at": user.registered_at,
            "country_code": user.country_code,
            "device_type": user.device_type,
            "acquisition_channel": user.acquisition_channel,
            "attributes": Json(user.attributes),
        }
        for user in users
    ]


def _fetch_user_ids(user_keys: list[str]) -> dict[str, int]:
    """Load database ids for the provided business user keys."""
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, user_key
                FROM users
                WHERE user_key = ANY(%s)
                """,
                (user_keys,),
            )
            return {user_key: user_id for user_id, user_key in cursor.fetchall()}


def _serialize_events(
    events: Iterable[EventIngestionRecord],
    user_ids: dict[str, int],
) -> list[dict]:
    """Prepare event rows for psycopg insertion."""
    rows: list[dict] = []

    for event in events:
        user_id = user_ids.get(event.user_key)
        if user_id is None:
            raise ValueError(f"user not found for event ingestion: {event.user_key}")

        event_value = None
        if event.event_value is not None:
            event_value = Decimal(event.event_value)

        rows.append(
            {
                "event_uuid": str(event.event_uuid),
                "user_id": user_id,
                "event_name": event.event_name,
                "event_timestamp": event.event_timestamp,
                "event_value": event_value,
                "event_properties": Json(event.event_properties),
            }
        )

    return rows


def ingest_dataset(dataset: SyntheticDataset) -> dict[str, int]:
    """Load validated synthetic users and events into PostgreSQL."""
    user_rows = _serialize_users(dataset.users)

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.executemany(USER_UPSERT_SQL, user_rows)
        connection.commit()

    user_ids = _fetch_user_ids([user.user_key for user in dataset.users])
    event_rows = _serialize_events(dataset.events, user_ids)

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.executemany(EVENT_INSERT_SQL, event_rows)
        connection.commit()

    return {
        "users_upserted": len(user_rows),
        "events_attempted": len(event_rows),
    }


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for generation and ingestion."""
    parser = argparse.ArgumentParser(description="Generate and ingest synthetic event data.")
    parser.add_argument("--users", type=int, default=250, help="Number of synthetic users.")
    parser.add_argument("--days", type=int, default=60, help="Length of event window in days.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility.")
    return parser.parse_args()


def main() -> None:
    """Generate a synthetic dataset and load it into PostgreSQL."""
    args = parse_args()
    dataset = generate_dataset(
        GenerationConfig(
            users_count=args.users,
            days=args.days,
            seed=args.seed,
        )
    )
    stats = ingest_dataset(dataset)
    print(stats)


if __name__ == "__main__":
    main()
