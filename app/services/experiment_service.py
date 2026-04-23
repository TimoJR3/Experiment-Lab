"""Service layer for creating experiments and storing deterministic assignments."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from psycopg.errors import UniqueViolation
from psycopg.rows import dict_row
from psycopg.types.json import Json

from app.db.session import get_db_connection
from app.experiments.assignment import AssignmentResult, VariantAllocation, assign_users
from app.schemas.experiments import (
    ExperimentAssignmentResponse,
    ExperimentCreateRequest,
    ExperimentStartRequest,
    ExperimentSummaryResponse,
    VariantAssignment,
)


class ExperimentServiceError(Exception):
    """Base exception for experiment service errors."""


class ExperimentNotFoundError(ExperimentServiceError):
    """Raised when an experiment does not exist."""


class ExperimentStatusError(ExperimentServiceError):
    """Raised when an operation is invalid for the current experiment status."""


class ExperimentValidationError(ExperimentServiceError):
    """Raised when experiment data fails service-level validation."""


@dataclass(frozen=True, slots=True)
class ExperimentRecord:
    """Stored experiment metadata needed by the service."""

    id: int
    experiment_key: str
    name: str
    status: str
    created_at: datetime


class ExperimentRepository:
    """Small repository wrapper around PostgreSQL operations."""

    def create_experiment(self, payload: ExperimentCreateRequest) -> ExperimentRecord:
        """Insert one draft experiment and its variants."""
        try:
            with get_db_connection() as connection:
                with connection.cursor(row_factory=dict_row) as cursor:
                    cursor.execute(
                        """
                        INSERT INTO experiments (
                            experiment_key,
                            name,
                            description,
                            hypothesis,
                            status,
                            owner_name,
                            primary_metric_key
                        )
                        VALUES (%s, %s, %s, %s, 'draft', %s, %s)
                        RETURNING id, experiment_key, name, status, created_at
                        """,
                        (
                            payload.experiment_key,
                            payload.name,
                            payload.description,
                            payload.hypothesis,
                            payload.owner_name,
                            payload.primary_metric_key,
                        ),
                    )
                    experiment_row = cursor.fetchone()

                    for variant in payload.variants:
                        cursor.execute(
                            """
                            INSERT INTO experiment_variants (
                                experiment_id,
                                variant_key,
                                name,
                                description,
                                is_control,
                                allocation_percent
                            )
                            VALUES (%s, %s, %s, %s, %s, %s)
                            """,
                            (
                                experiment_row["id"],
                                variant.variant_key,
                                variant.name,
                                variant.description,
                                variant.is_control,
                                variant.allocation_percent,
                            ),
                        )

                connection.commit()
        except UniqueViolation as exc:
            raise ExperimentValidationError("experiment_key already exists") from exc

        return ExperimentRecord(**experiment_row)

    def get_experiment(self, experiment_key: str) -> ExperimentRecord | None:
        """Fetch experiment metadata by business key."""
        with get_db_connection() as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    """
                    SELECT id, experiment_key, name, status, created_at
                    FROM experiments
                    WHERE experiment_key = %s
                    """,
                    (experiment_key,),
                )
                row = cursor.fetchone()

        if row is None:
            return None
        return ExperimentRecord(**row)

    def get_variants(self, experiment_id: int) -> list[VariantAllocation]:
        """Fetch experiment variants ordered for deterministic allocation."""
        with get_db_connection() as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    """
                    SELECT id, variant_key, allocation_percent
                    FROM experiment_variants
                    WHERE experiment_id = %s
                    ORDER BY is_control DESC, id ASC
                    """,
                    (experiment_id,),
                )
                rows = cursor.fetchall()

        return [
            VariantAllocation(
                variant_id=row["id"],
                variant_key=row["variant_key"],
                allocation_percent=Decimal(str(row["allocation_percent"])),
            )
            for row in rows
        ]

    def count_users(self, user_ids: list[int]) -> int:
        """Count how many requested users already exist in the database."""
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM users
                    WHERE id = ANY(%s)
                    """,
                    (user_ids,),
                )
                return int(cursor.fetchone()[0])

    def update_experiment_status(
        self,
        experiment_id: int,
        status: str,
        start_at: datetime | None = None,
    ) -> None:
        """Persist experiment status transitions."""
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE experiments
                    SET status = %s,
                        start_at = COALESCE(%s, start_at)
                    WHERE id = %s
                    """,
                    (status, start_at, experiment_id),
                )
            connection.commit()

    def insert_assignments(
        self,
        experiment_id: int,
        assignments: list[AssignmentResult],
        assignment_source: str,
    ) -> None:
        """Store assignments and rely on the DB uniqueness constraint for duplicates."""
        rows = [
            (
                experiment_id,
                assignment.variant_id,
                assignment.user_id,
                assignment_source,
                assignment.assignment_bucket,
                Json({"bucket": str(assignment.assignment_bucket)}),
            )
            for assignment in assignments
        ]

        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.executemany(
                    """
                    INSERT INTO experiment_assignments (
                        experiment_id,
                        variant_id,
                        user_id,
                        assignment_source,
                        assignment_bucket,
                        assignment_metadata
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (experiment_id, user_id) DO NOTHING
                    """,
                    rows,
                )
            connection.commit()


class ExperimentService:
    """High-level experiment operations with clear status checks."""

    def __init__(self, repository: ExperimentRepository | None = None) -> None:
        self.repository = repository or ExperimentRepository()

    def create_experiment(self, payload: ExperimentCreateRequest) -> ExperimentSummaryResponse:
        """Create one draft experiment with variants."""
        record = self.repository.create_experiment(payload)
        return ExperimentSummaryResponse(
            experiment_id=record.id,
            experiment_key=record.experiment_key,
            name=record.name,
            status=record.status,
            created_at=record.created_at,
        )

    def start_experiment(
        self,
        experiment_key: str,
        payload: ExperimentStartRequest,
    ) -> ExperimentAssignmentResponse:
        """Move experiment to running and persist deterministic assignments."""
        experiment = self.repository.get_experiment(experiment_key)
        if experiment is None:
            raise ExperimentNotFoundError(f"experiment not found: {experiment_key}")

        if experiment.status == "completed":
            raise ExperimentStatusError("completed experiments cannot receive new assignments")

        variants = self.repository.get_variants(experiment.id)
        if len(variants) < 2:
            raise ExperimentValidationError("experiment must contain at least two variants")

        existing_users = self.repository.count_users(payload.user_ids)
        if existing_users != len(payload.user_ids):
            raise ExperimentValidationError("some user_ids do not exist in the database")

        assignment_results = assign_users(
            experiment_key=experiment.experiment_key,
            user_ids=payload.user_ids,
            variants=variants,
        )
        self.repository.insert_assignments(
            experiment_id=experiment.id,
            assignments=assignment_results,
            assignment_source=payload.assignment_source,
        )

        if experiment.status == "draft":
            self.repository.update_experiment_status(
                experiment_id=experiment.id,
                status="running",
                start_at=datetime.now(timezone.utc),
            )
            experiment_status = "running"
        else:
            experiment_status = experiment.status

        return ExperimentAssignmentResponse(
            experiment_id=experiment.id,
            experiment_key=experiment.experiment_key,
            status=experiment_status,
            assigned_users=len(assignment_results),
            assignments=[
                VariantAssignment(
                    user_id=item.user_id,
                    variant_id=item.variant_id,
                    variant_key=item.variant_key,
                    assignment_bucket=item.assignment_bucket,
                )
                for item in assignment_results
            ],
        )
