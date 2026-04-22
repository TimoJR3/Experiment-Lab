"""Tests for synthetic data generation and validation."""

from datetime import timezone
from uuid import uuid4

import pytest

from app.experiments.synthetic_data import GenerationConfig, generate_dataset
from app.schemas.events import EventIngestionRecord, UserIngestionRecord, validate_dataset


def test_generate_dataset_returns_users_and_events() -> None:
    """Synthetic generator should create both users and events."""
    dataset = generate_dataset(GenerationConfig(users_count=25, days=45, seed=7))

    assert len(dataset.users) == 25
    assert len(dataset.events) > 25
    assert {event.event_name for event in dataset.events}.issuperset(
        {"app_open", "view_item", "add_to_cart", "purchase"}
    )


def test_revenue_events_have_positive_values() -> None:
    """Revenue events should always include a positive numeric value."""
    dataset = generate_dataset(GenerationConfig(users_count=80, days=60, seed=11))
    revenue_events = [
        event
        for event in dataset.events
        if event.event_name in {"purchase", "subscription_start", "subscription_renewal"}
    ]

    assert revenue_events
    assert all(event.event_value is not None and event.event_value > 0 for event in revenue_events)


def test_events_happen_after_user_registration() -> None:
    """Generated timestamps should respect user registration time."""
    dataset = generate_dataset(GenerationConfig(users_count=30, days=30, seed=19))
    users_by_key = {user.user_key: user for user in dataset.users}

    for event in dataset.events:
        assert event.event_timestamp >= users_by_key[event.user_key].registered_at
        assert event.event_timestamp.tzinfo == timezone.utc


def test_validation_rejects_purchase_without_value() -> None:
    """Validation should fail for malformed revenue events."""
    with pytest.raises(ValueError):
        EventIngestionRecord(
            event_uuid=uuid4(),
            user_key="synthetic_user_00001",
            event_name="purchase",
            event_timestamp="2026-01-01T00:00:00+00:00",
            event_value=None,
            event_properties={},
        )


def test_validation_rejects_event_before_registration() -> None:
    """Validation should reject events that happen before registration."""
    user = UserIngestionRecord(
        user_key="synthetic_user_00002",
        registered_at="2026-01-03T00:00:00+00:00",
        country_code="RU",
        device_type="android",
        acquisition_channel="ads",
        attributes={"activity_segment": "medium"},
    )
    event = EventIngestionRecord(
        event_uuid=uuid4(),
        user_key=user.user_key,
        event_name="app_open",
        event_timestamp="2026-01-02T23:59:00+00:00",
        event_properties={},
    )

    with pytest.raises(ValueError):
        validate_dataset([user], [event])
