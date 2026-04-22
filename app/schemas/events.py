"""Schemas and validation helpers for synthetic event ingestion."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

ALLOWED_EVENT_NAMES = {
    "app_open",
    "view_item",
    "add_to_cart",
    "purchase",
    "subscription_start",
    "subscription_renewal",
}

REVENUE_EVENT_NAMES = {
    "purchase",
    "subscription_start",
    "subscription_renewal",
}


class UserIngestionRecord(BaseModel):
    """Validated user payload for synthetic data ingestion."""

    user_key: str
    registered_at: datetime
    country_code: str
    device_type: str
    acquisition_channel: str
    attributes: dict[str, Any] = Field(default_factory=dict)

    @field_validator("user_key", "country_code", "device_type", "acquisition_channel")
    @classmethod
    def value_must_not_be_blank(cls, value: str) -> str:
        """Reject blank string values for required user fields."""
        if not value.strip():
            raise ValueError("value must not be blank")
        return value

    @field_validator("registered_at")
    @classmethod
    def registered_at_must_be_timezone_aware(cls, value: datetime) -> datetime:
        """Require timezone-aware timestamps."""
        if value.tzinfo is None:
            raise ValueError("registered_at must be timezone-aware")
        return value


class EventIngestionRecord(BaseModel):
    """Validated event payload for synthetic data ingestion."""

    event_uuid: UUID
    user_key: str
    event_name: str
    event_timestamp: datetime
    event_value: Decimal | None = None
    event_properties: dict[str, Any] = Field(default_factory=dict)

    @field_validator("user_key")
    @classmethod
    def user_key_must_not_be_blank(cls, value: str) -> str:
        """Reject blank user keys."""
        if not value.strip():
            raise ValueError("user_key must not be blank")
        return value

    @field_validator("event_name")
    @classmethod
    def event_name_must_be_supported(cls, value: str) -> str:
        """Restrict events to the product funnel supported by the project."""
        if value not in ALLOWED_EVENT_NAMES:
            raise ValueError(f"unsupported event_name: {value}")
        return value

    @field_validator("event_timestamp")
    @classmethod
    def event_timestamp_must_be_timezone_aware(cls, value: datetime) -> datetime:
        """Require timezone-aware event timestamps."""
        if value.tzinfo is None:
            raise ValueError("event_timestamp must be timezone-aware")
        return value

    @field_validator("event_value")
    @classmethod
    def event_value_must_be_non_negative(cls, value: Decimal | None) -> Decimal | None:
        """Reject negative numeric event values."""
        if value is not None and value < 0:
            raise ValueError("event_value must be non-negative")
        return value

    def model_post_init(self, __context: Any) -> None:
        """Enforce revenue values only for revenue events."""
        if self.event_name in REVENUE_EVENT_NAMES and self.event_value is None:
            raise ValueError("revenue events must include event_value")


def validate_dataset(
    users: list[UserIngestionRecord],
    events: list[EventIngestionRecord],
) -> None:
    """Run cross-record validation for generated synthetic data."""
    users_by_key = {user.user_key: user for user in users}

    if len(users_by_key) != len(users):
        raise ValueError("user_key values must be unique inside one dataset")

    for user in users:
        if user.registered_at.tzinfo is None:
            raise ValueError("registered_at must be timezone-aware")

    seen_event_ids: set[UUID] = set()

    for event in events:
        if event.event_uuid in seen_event_ids:
            raise ValueError("event_uuid values must be unique inside one dataset")
        seen_event_ids.add(event.event_uuid)

        if event.event_name not in ALLOWED_EVENT_NAMES:
            raise ValueError(f"unsupported event_name: {event.event_name}")

        if event.event_name in REVENUE_EVENT_NAMES and event.event_value is None:
            raise ValueError("revenue events must include event_value")

        if event.event_value is not None and event.event_value < 0:
            raise ValueError("event_value must be non-negative")

        if event.event_timestamp.tzinfo is None:
            raise ValueError("event_timestamp must be timezone-aware")

        user = users_by_key.get(event.user_key)
        if user is None:
            raise ValueError(f"event references unknown user_key: {event.user_key}")

        if event.event_timestamp < user.registered_at:
            raise ValueError("event_timestamp must not be earlier than user registration")
