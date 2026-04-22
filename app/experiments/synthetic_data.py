"""Synthetic data generator for portfolio-friendly product events."""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from app.schemas.events import EventIngestionRecord, UserIngestionRecord, validate_dataset


@dataclass(frozen=True, slots=True)
class ActivityProfile:
    """User activity profile used to shape the synthetic funnel."""

    name: str
    active_day_ratio: tuple[float, float]
    sessions_per_day: tuple[int, int]
    item_views_per_session: tuple[int, int]
    view_probability: float
    cart_probability: float
    purchase_probability: float
    subscription_probability: float
    renewal_probability: float


@dataclass(frozen=True, slots=True)
class GenerationConfig:
    """Configuration for synthetic user and event generation."""

    users_count: int = 250
    days: int = 60
    seed: int = 42
    start_at: datetime | None = None


@dataclass(slots=True)
class SyntheticDataset:
    """Generated users and events ready for validation or ingestion."""

    users: list[UserIngestionRecord]
    events: list[EventIngestionRecord]


ACTIVITY_PROFILES = (
    ActivityProfile(
        name="low",
        active_day_ratio=(0.05, 0.14),
        sessions_per_day=(1, 2),
        item_views_per_session=(1, 3),
        view_probability=0.72,
        cart_probability=0.14,
        purchase_probability=0.07,
        subscription_probability=0.03,
        renewal_probability=0.62,
    ),
    ActivityProfile(
        name="medium",
        active_day_ratio=(0.15, 0.32),
        sessions_per_day=(1, 3),
        item_views_per_session=(2, 4),
        view_probability=0.84,
        cart_probability=0.24,
        purchase_probability=0.12,
        subscription_probability=0.05,
        renewal_probability=0.7,
    ),
    ActivityProfile(
        name="high",
        active_day_ratio=(0.33, 0.58),
        sessions_per_day=(2, 4),
        item_views_per_session=(3, 6),
        view_probability=0.93,
        cart_probability=0.38,
        purchase_probability=0.2,
        subscription_probability=0.08,
        renewal_probability=0.78,
    ),
)

COUNTRIES = ("RU", "KZ", "BY", "UZ")
DEVICES = ("ios", "android", "web")
CHANNELS = ("organic", "ads", "referral", "email")
ITEM_CATEGORIES = ("electronics", "home", "beauty", "books", "sport")
SUBSCRIPTION_PRICES = (Decimal("9.99"), Decimal("14.99"), Decimal("19.99"))


def _resolved_start_at(config: GenerationConfig) -> datetime:
    """Resolve the start of the generation window."""
    if config.start_at is not None:
        return config.start_at
    return datetime.now(timezone.utc) - timedelta(days=config.days)


def _make_event_uuid(user_key: str, event_name: str, event_timestamp: datetime, ordinal: int) -> str:
    """Build a stable UUID so ingestion can be idempotent."""
    source = f"{user_key}|{event_name}|{event_timestamp.isoformat()}|{ordinal}"
    return str(uuid5(NAMESPACE_URL, source))


def _pick_activity_profile(rng: random.Random) -> ActivityProfile:
    """Sample user activity segment with a practical distribution."""
    return rng.choices(
        population=ACTIVITY_PROFILES,
        weights=(0.55, 0.3, 0.15),
        k=1,
    )[0]


def _build_user_record(
    index: int,
    registered_at: datetime,
    profile: ActivityProfile,
    rng: random.Random,
) -> UserIngestionRecord:
    """Create one validated synthetic user."""
    return UserIngestionRecord(
        user_key=f"synthetic_user_{index:05d}",
        registered_at=registered_at,
        country_code=rng.choices(COUNTRIES, weights=(0.5, 0.2, 0.15, 0.15), k=1)[0],
        device_type=rng.choices(DEVICES, weights=(0.35, 0.45, 0.2), k=1)[0],
        acquisition_channel=rng.choices(CHANNELS, weights=(0.45, 0.25, 0.15, 0.15), k=1)[0],
        attributes={
            "activity_segment": profile.name,
            "preferred_category": rng.choice(ITEM_CATEGORIES),
        },
    )


def generate_users(config: GenerationConfig) -> list[UserIngestionRecord]:
    """Generate a synthetic user base with different activity levels."""
    rng = random.Random(config.seed)
    start_at = _resolved_start_at(config)
    end_at = start_at + timedelta(days=config.days)
    latest_registration = end_at - timedelta(days=max(5, config.days // 5))
    registration_window_seconds = max(
        1,
        int((latest_registration - start_at).total_seconds()),
    )

    users: list[UserIngestionRecord] = []
    for index in range(1, config.users_count + 1):
        profile = _pick_activity_profile(rng)
        registered_at = start_at + timedelta(seconds=rng.randint(0, registration_window_seconds))
        users.append(_build_user_record(index, registered_at, profile, rng))
    return users


def _purchase_amount(rng: random.Random) -> Decimal:
    """Sample a purchase amount with a few realistic price buckets."""
    base_price = Decimal(str(rng.choice((12.99, 18.50, 24.99, 39.99, 59.99, 89.99))))
    noise = Decimal(str(round(rng.uniform(-2.0, 3.5), 2)))
    return max(Decimal("4.99"), base_price + noise).quantize(Decimal("0.01"))


def _append_event(
    events: list[EventIngestionRecord],
    user_key: str,
    event_name: str,
    event_timestamp: datetime,
    ordinal: int,
    event_value: Decimal | None = None,
    event_properties: dict[str, Any] | None = None,
) -> int:
    """Append one validated event and return the next ordinal counter."""
    events.append(
        EventIngestionRecord(
            event_uuid=_make_event_uuid(user_key, event_name, event_timestamp, ordinal),
            user_key=user_key,
            event_name=event_name,
            event_timestamp=event_timestamp,
            event_value=event_value,
            event_properties=event_properties or {},
        )
    )
    return ordinal + 1


def generate_events(
    users: list[UserIngestionRecord],
    config: GenerationConfig,
) -> list[EventIngestionRecord]:
    """Generate a realistic event stream for an e-commerce style product app."""
    rng = random.Random(config.seed)
    start_at = _resolved_start_at(config)
    end_at = start_at + timedelta(days=config.days)
    events: list[EventIngestionRecord] = []

    for user in users:
        profile_name = str(user.attributes["activity_segment"])
        profile = next(item for item in ACTIVITY_PROFILES if item.name == profile_name)
        available_days = max(1, (end_at.date() - user.registered_at.date()).days + 1)
        ratio = rng.uniform(*profile.active_day_ratio)
        active_days = min(available_days, max(1, int(available_days * ratio)))
        active_offsets = sorted(rng.sample(range(available_days), k=active_days))
        next_ordinal = 1
        subscription_started_at: datetime | None = None
        subscription_price: Decimal | None = None

        for day_offset in active_offsets:
            day_start = datetime.combine(
                user.registered_at.date() + timedelta(days=day_offset),
                datetime.min.time(),
                tzinfo=timezone.utc,
            )
            sessions_count = rng.randint(*profile.sessions_per_day)

            for session_idx in range(sessions_count):
                session_hour = rng.randint(8, 22)
                session_minute = rng.randint(0, 59)
                session_start = day_start + timedelta(hours=session_hour, minutes=session_minute)
                if session_start < user.registered_at or session_start > end_at:
                    continue

                session_id = f"{user.user_key}-d{day_offset}-s{session_idx + 1}"
                next_ordinal = _append_event(
                    events=events,
                    user_key=user.user_key,
                    event_name="app_open",
                    event_timestamp=session_start,
                    ordinal=next_ordinal,
                    event_properties={
                        "session_id": session_id,
                        "device_type": user.device_type,
                    },
                )

                if rng.random() > profile.view_probability:
                    continue

                views_count = rng.randint(*profile.item_views_per_session)
                selected_category = str(user.attributes["preferred_category"])
                last_item_price = Decimal("0.00")

                for view_idx in range(views_count):
                    item_time = session_start + timedelta(minutes=2 + view_idx * rng.randint(1, 4))
                    last_item_price = _purchase_amount(rng)
                    next_ordinal = _append_event(
                        events=events,
                        user_key=user.user_key,
                        event_name="view_item",
                        event_timestamp=item_time,
                        ordinal=next_ordinal,
                        event_properties={
                            "session_id": session_id,
                            "item_id": f"item_{rng.randint(1000, 9999)}",
                            "category": selected_category,
                            "listed_price": float(last_item_price),
                        },
                    )

                if rng.random() > profile.cart_probability:
                    continue

                cart_time = session_start + timedelta(minutes=rng.randint(5, 20))
                next_ordinal = _append_event(
                    events=events,
                    user_key=user.user_key,
                    event_name="add_to_cart",
                    event_timestamp=cart_time,
                    ordinal=next_ordinal,
                    event_properties={
                        "session_id": session_id,
                        "items_in_cart": rng.randint(1, 3),
                        "category": selected_category,
                    },
                )

                if rng.random() > profile.purchase_probability:
                    continue

                purchase_time = cart_time + timedelta(minutes=rng.randint(1, 15))
                purchase_value = (last_item_price * Decimal(str(rng.uniform(0.9, 1.15)))).quantize(
                    Decimal("0.01")
                )
                next_ordinal = _append_event(
                    events=events,
                    user_key=user.user_key,
                    event_name="purchase",
                    event_timestamp=purchase_time,
                    ordinal=next_ordinal,
                    event_value=purchase_value,
                    event_properties={
                        "session_id": session_id,
                        "currency": "USD",
                        "items_count": rng.randint(1, 3),
                        "payment_method": rng.choice(("card", "wallet")),
                    },
                )

                if subscription_started_at is None and rng.random() < profile.subscription_probability:
                    subscription_started_at = purchase_time + timedelta(minutes=rng.randint(10, 90))
                    subscription_price = rng.choice(SUBSCRIPTION_PRICES)
                    next_ordinal = _append_event(
                        events=events,
                        user_key=user.user_key,
                        event_name="subscription_start",
                        event_timestamp=subscription_started_at,
                        ordinal=next_ordinal,
                        event_value=subscription_price,
                        event_properties={
                            "session_id": session_id,
                            "billing_period_days": 30,
                            "plan_name": rng.choice(("basic", "plus")),
                        },
                    )

        if subscription_started_at is not None and subscription_price is not None:
            renewal_time = subscription_started_at + timedelta(days=30)
            while renewal_time <= end_at:
                if rng.random() <= profile.renewal_probability:
                    next_ordinal = _append_event(
                        events=events,
                        user_key=user.user_key,
                        event_name="subscription_renewal",
                        event_timestamp=renewal_time,
                        ordinal=next_ordinal,
                        event_value=subscription_price,
                        event_properties={
                            "billing_period_days": 30,
                            "plan_name": "renewal",
                        },
                    )
                renewal_time += timedelta(days=30)

    events.sort(key=lambda item: (item.event_timestamp, item.user_key, item.event_name))
    return events


def generate_dataset(config: GenerationConfig) -> SyntheticDataset:
    """Generate and validate a full synthetic dataset."""
    users = generate_users(config)
    events = generate_events(users, config)
    validate_dataset(users, events)
    return SyntheticDataset(users=users, events=events)


def summarize_dataset(dataset: SyntheticDataset) -> dict[str, Any]:
    """Build a lightweight dataset summary for CLI output."""
    event_counts: dict[str, int] = {}
    revenue_total = Decimal("0.00")

    for event in dataset.events:
        event_counts[event.event_name] = event_counts.get(event.event_name, 0) + 1
        if event.event_value is not None:
            revenue_total += event.event_value

    return {
        "users": len(dataset.users),
        "events": len(dataset.events),
        "event_counts": event_counts,
        "total_revenue": float(revenue_total.quantize(Decimal("0.01"))),
    }


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for dataset generation."""
    parser = argparse.ArgumentParser(description="Generate synthetic Experiment Lab data.")
    parser.add_argument("--users", type=int, default=250, help="Number of synthetic users.")
    parser.add_argument("--days", type=int, default=60, help="Length of event window in days.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility.")
    parser.add_argument(
        "--preview-events",
        type=int,
        default=5,
        help="How many first events to print as JSON preview.",
    )
    return parser.parse_args()


def main() -> None:
    """Generate synthetic data and print a compact preview."""
    args = parse_args()
    dataset = generate_dataset(
        GenerationConfig(
            users_count=args.users,
            days=args.days,
            seed=args.seed,
        )
    )

    print(json.dumps(summarize_dataset(dataset), indent=2))
    preview_rows = [event.model_dump(mode="json") for event in dataset.events[: args.preview_events]]
    print(json.dumps(preview_rows, indent=2))


if __name__ == "__main__":
    main()
