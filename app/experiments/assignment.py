"""Deterministic assignment engine for control/treatment experiment splits."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from hashlib import md5


@dataclass(frozen=True, slots=True)
class VariantAllocation:
    """Variant allocation information used by the assignment engine."""

    variant_id: int
    variant_key: str
    allocation_percent: Decimal


@dataclass(frozen=True, slots=True)
class AssignmentResult:
    """Deterministic assignment result for one user."""

    user_id: int
    variant_id: int
    variant_key: str
    assignment_bucket: Decimal


def compute_assignment_bucket(experiment_key: str, user_id: int) -> Decimal:
    """Map one user into a stable bucket from 0.000000 to 99.999999."""
    raw_value = f"{experiment_key}:{user_id}".encode("utf-8")
    hash_int = int(md5(raw_value, usedforsecurity=False).hexdigest(), 16)
    normalized = Decimal(hash_int % 1_000_000) / Decimal("10000")
    return normalized.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)


def assign_user_to_variant(
    experiment_key: str,
    user_id: int,
    variants: list[VariantAllocation],
) -> AssignmentResult:
    """Assign one user to a variant via cumulative percentage buckets."""
    if len(variants) < 2:
        raise ValueError("at least two variants are required for assignment")

    total_allocation = sum(variant.allocation_percent for variant in variants)
    if total_allocation != Decimal("100"):
        raise ValueError("variant allocation must sum to 100")

    bucket = compute_assignment_bucket(experiment_key=experiment_key, user_id=user_id)
    cumulative = Decimal("0")

    for variant in variants:
        cumulative += variant.allocation_percent
        if bucket < cumulative:
            return AssignmentResult(
                user_id=user_id,
                variant_id=variant.variant_id,
                variant_key=variant.variant_key,
                assignment_bucket=bucket,
            )

    last_variant = variants[-1]
    return AssignmentResult(
        user_id=user_id,
        variant_id=last_variant.variant_id,
        variant_key=last_variant.variant_key,
        assignment_bucket=bucket,
    )


def assign_users(
    experiment_key: str,
    user_ids: list[int],
    variants: list[VariantAllocation],
) -> list[AssignmentResult]:
    """Assign multiple users with deterministic hash-based logic."""
    return [
        assign_user_to_variant(
            experiment_key=experiment_key,
            user_id=user_id,
            variants=variants,
        )
        for user_id in user_ids
    ]
