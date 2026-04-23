"""Schemas for experiment creation, execution, and assignment responses."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator, model_validator


class ExperimentVariantInput(BaseModel):
    """Input schema for experiment variants."""

    variant_key: str
    name: str
    description: str | None = None
    is_control: bool = False
    allocation_percent: Decimal = Field(..., gt=0, le=100)

    @field_validator("variant_key", "name")
    @classmethod
    def must_not_be_blank(cls, value: str) -> str:
        """Reject blank required fields."""
        if not value.strip():
            raise ValueError("value must not be blank")
        return value


class ExperimentCreateRequest(BaseModel):
    """Payload for creating a draft experiment."""

    experiment_key: str
    name: str
    description: str | None = None
    hypothesis: str | None = None
    owner_name: str | None = None
    primary_metric_key: str | None = None
    variants: list[ExperimentVariantInput]

    @field_validator("experiment_key", "name")
    @classmethod
    def required_strings_must_not_be_blank(cls, value: str) -> str:
        """Reject blank keys and names."""
        if not value.strip():
            raise ValueError("value must not be blank")
        return value

    @model_validator(mode="after")
    def validate_variants(self) -> "ExperimentCreateRequest":
        """Ensure the experiment has a valid control/treatment split."""
        if len(self.variants) < 2:
            raise ValueError("an experiment must contain at least two variants")

        control_count = sum(1 for variant in self.variants if variant.is_control)
        if control_count != 1:
            raise ValueError("an experiment must contain exactly one control variant")

        total_allocation = sum(variant.allocation_percent for variant in self.variants)
        if total_allocation != Decimal("100"):
            raise ValueError("variant allocation_percent values must sum to 100")

        variant_keys = [variant.variant_key for variant in self.variants]
        if len(set(variant_keys)) != len(variant_keys):
            raise ValueError("variant_key values must be unique within one experiment")

        return self


class ExperimentStartRequest(BaseModel):
    """Payload for starting an experiment and assigning users."""

    user_ids: list[int]
    assignment_source: str = "hash"

    @field_validator("assignment_source")
    @classmethod
    def assignment_source_must_not_be_blank(cls, value: str) -> str:
        """Reject blank assignment sources."""
        if not value.strip():
            raise ValueError("assignment_source must not be blank")
        return value

    @model_validator(mode="after")
    def validate_user_ids(self) -> "ExperimentStartRequest":
        """Require at least one user and unique ids inside the request."""
        if not self.user_ids:
            raise ValueError("user_ids must not be empty")

        if len(set(self.user_ids)) != len(self.user_ids):
            raise ValueError("user_ids must be unique within one request")

        return self


class VariantAssignment(BaseModel):
    """Assignment result for one user."""

    user_id: int
    variant_id: int
    variant_key: str
    assignment_bucket: Decimal


class ExperimentAssignmentResponse(BaseModel):
    """Response after starting an experiment and storing assignments."""

    experiment_id: int
    experiment_key: str
    status: str
    assigned_users: int
    assignments: list[VariantAssignment]


class ExperimentSummaryResponse(BaseModel):
    """Basic API response for a created experiment."""

    experiment_id: int
    experiment_key: str
    name: str
    status: str
    created_at: datetime
