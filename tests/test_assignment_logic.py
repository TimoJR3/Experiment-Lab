"""Tests for deterministic experiment assignment logic and service rules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.experiments.assignment import VariantAllocation, assign_user_to_variant, assign_users
from app.schemas.experiments import ExperimentCreateRequest, ExperimentStartRequest
from app.services.experiment_service import (
    ExperimentNotFoundError,
    ExperimentRecord,
    ExperimentService,
    ExperimentStatusError,
)


def _variants() -> list[VariantAllocation]:
    return [
        VariantAllocation(variant_id=1, variant_key="control", allocation_percent=Decimal("50")),
        VariantAllocation(variant_id=2, variant_key="treatment", allocation_percent=Decimal("50")),
    ]


def test_assignment_is_deterministic_for_same_user() -> None:
    """The same user should always land in the same variant."""
    first = assign_user_to_variant("checkout_v2", user_id=101, variants=_variants())
    second = assign_user_to_variant("checkout_v2", user_id=101, variants=_variants())

    assert first.variant_key == second.variant_key
    assert first.assignment_bucket == second.assignment_bucket


def test_assignment_supports_multiple_users() -> None:
    """Batch assignment should produce one result per input user."""
    results = assign_users("checkout_v2", user_ids=[1, 2, 3, 4], variants=_variants())

    assert len(results) == 4
    assert {item.variant_key for item in results}.issubset({"control", "treatment"})


def test_assignment_distribution_is_reasonable_for_large_sample() -> None:
    """Hash split should be close to configured allocation on a larger sample."""
    results = assign_users("checkout_v2", user_ids=list(range(1, 1001)), variants=_variants())
    control_share = sum(item.variant_key == "control" for item in results) / len(results)

    assert 0.45 <= control_share <= 0.55


def test_assignment_rejects_invalid_allocation_sum() -> None:
    """Assignment should fail when variant allocations do not sum to 100."""
    bad_variants = [
        VariantAllocation(variant_id=1, variant_key="control", allocation_percent=Decimal("70")),
        VariantAllocation(variant_id=2, variant_key="treatment", allocation_percent=Decimal("20")),
    ]

    with pytest.raises(ValueError):
        assign_user_to_variant("checkout_v2", user_id=101, variants=bad_variants)


def test_experiment_create_request_requires_exactly_one_control() -> None:
    """Experiment payload must declare one control variant."""
    with pytest.raises(ValueError):
        ExperimentCreateRequest(
            experiment_key="bad_experiment",
            name="Bad Experiment",
            variants=[
                {
                    "variant_key": "control",
                    "name": "Control",
                    "is_control": True,
                    "allocation_percent": "60",
                },
                {
                    "variant_key": "control_2",
                    "name": "Control 2",
                    "is_control": True,
                    "allocation_percent": "40",
                },
            ],
        )


@dataclass
class FakeRepository:
    """Tiny fake repository for service-level tests."""

    experiment: ExperimentRecord | None
    variants: list[VariantAllocation]
    user_count: int
    inserted_assignments: list = None
    updated_status: str | None = None

    def __post_init__(self) -> None:
        self.inserted_assignments = []

    def create_experiment(self, payload: ExperimentCreateRequest) -> ExperimentRecord:
        return ExperimentRecord(
            id=1,
            experiment_key=payload.experiment_key,
            name=payload.name,
            status="draft",
            created_at=datetime.now(timezone.utc),
        )

    def get_experiment(self, experiment_key: str) -> ExperimentRecord | None:
        return self.experiment

    def get_variants(self, experiment_id: int) -> list[VariantAllocation]:
        return self.variants

    def count_users(self, user_ids: list[int]) -> int:
        return self.user_count

    def update_experiment_status(self, experiment_id: int, status: str, start_at: datetime | None = None) -> None:
        self.updated_status = status

    def insert_assignments(self, experiment_id: int, assignments: list, assignment_source: str) -> None:
        self.inserted_assignments = assignments


def test_service_rejects_missing_experiment() -> None:
    """Starting a missing experiment should raise a clear error."""
    service = ExperimentService(repository=FakeRepository(experiment=None, variants=_variants(), user_count=2))

    with pytest.raises(ExperimentNotFoundError):
        service.start_experiment(
            experiment_key="missing",
            payload=ExperimentStartRequest(user_ids=[1, 2]),
        )


def test_service_rejects_completed_experiment() -> None:
    """Completed experiments must not accept new assignments."""
    service = ExperimentService(
        repository=FakeRepository(
            experiment=ExperimentRecord(
                id=1,
                experiment_key="checkout_v2",
                name="Checkout Test",
                status="completed",
                created_at=datetime.now(timezone.utc),
            ),
            variants=_variants(),
            user_count=2,
        )
    )

    with pytest.raises(ExperimentStatusError):
        service.start_experiment(
            experiment_key="checkout_v2",
            payload=ExperimentStartRequest(user_ids=[1, 2]),
        )


def test_service_starts_draft_experiment_and_assigns_users() -> None:
    """Draft experiments should move to running and persist assignments."""
    repository = FakeRepository(
        experiment=ExperimentRecord(
            id=7,
            experiment_key="checkout_v2",
            name="Checkout Test",
            status="draft",
            created_at=datetime.now(timezone.utc),
        ),
        variants=_variants(),
        user_count=3,
    )
    service = ExperimentService(repository=repository)

    response = service.start_experiment(
        experiment_key="checkout_v2",
        payload=ExperimentStartRequest(user_ids=[11, 12, 13]),
    )

    assert response.status == "running"
    assert response.assigned_users == 3
    assert repository.updated_status == "running"
    assert len(repository.inserted_assignments) == 3
