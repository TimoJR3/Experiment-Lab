"""Read-only service for API endpoints consumed by the Streamlit dashboard."""

from __future__ import annotations

from psycopg.rows import dict_row

from app.db.session import get_db_connection
from app.experiments.metrics import analyze_experiment_metrics
from app.schemas.dashboard import (
    AssignmentGroupSummary,
    EventCountItem,
    EventsSummaryResponse,
    ExperimentAssignmentsResponse,
    ExperimentDetailResponse,
    ExperimentListItem,
    ExperimentMetricsResponse,
    ExperimentSavedResultsResponse,
    UsersSummaryResponse,
)
from app.schemas.metrics import MetricResultResponse
from app.services.experiment_service import ExperimentNotFoundError, ExperimentValidationError
from app.services.metrics_service import MetricsRepository


class DashboardRepository:
    """PostgreSQL queries for dashboard read models."""

    def list_experiments(self) -> list[ExperimentListItem]:
        """Return all experiments with lightweight counts."""
        with get_db_connection() as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    """
                    SELECT
                        e.id,
                        e.experiment_key,
                        e.name,
                        e.status,
                        e.start_at,
                        e.end_at,
                        COUNT(DISTINCT v.id)::int AS variants_count,
                        COUNT(DISTINCT a.user_id)::int AS assignments_count
                    FROM experiments e
                    LEFT JOIN experiment_variants v
                        ON v.experiment_id = e.id
                    LEFT JOIN experiment_assignments a
                        ON a.experiment_id = e.id
                    GROUP BY e.id
                    ORDER BY e.created_at DESC
                    """
                )
                rows = cursor.fetchall()

        return [ExperimentListItem(**row) for row in rows]

    def get_experiment(self, experiment_id: int) -> ExperimentDetailResponse | None:
        """Return one experiment by id."""
        with get_db_connection() as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    """
                    SELECT
                        id,
                        experiment_key,
                        name,
                        description,
                        hypothesis,
                        status,
                        start_at,
                        end_at,
                        owner_name,
                        primary_metric_key,
                        created_at,
                        updated_at
                    FROM experiments
                    WHERE id = %s
                    """,
                    (experiment_id,),
                )
                row = cursor.fetchone()

        if row is None:
            return None
        return ExperimentDetailResponse(**row)

    def get_assignments(self, experiment_id: int) -> ExperimentAssignmentsResponse:
        """Return assignment counts by variant."""
        with get_db_connection() as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    """
                    SELECT
                        v.id AS variant_id,
                        v.variant_key,
                        v.is_control,
                        COUNT(a.user_id)::int AS users_count
                    FROM experiment_variants v
                    LEFT JOIN experiment_assignments a
                        ON a.variant_id = v.id
                    WHERE v.experiment_id = %s
                    GROUP BY v.id, v.variant_key, v.is_control
                    ORDER BY v.is_control DESC, v.id
                    """,
                    (experiment_id,),
                )
                rows = cursor.fetchall()

        groups = [AssignmentGroupSummary(**row) for row in rows]
        return ExperimentAssignmentsResponse(
            experiment_id=experiment_id,
            total_assigned=sum(group.users_count for group in groups),
            groups=groups,
        )

    def get_saved_results(self, experiment_id: int) -> ExperimentSavedResultsResponse:
        """Load saved experiment analysis results."""
        with get_db_connection() as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    """
                    SELECT
                        md.metric_key,
                        md.metric_name,
                        baseline.variant_key AS baseline_variant_key,
                        compared.variant_key AS compared_variant_key,
                        er.sample_size_baseline,
                        er.sample_size_compared,
                        er.baseline_value::float AS baseline_value,
                        er.compared_value::float AS compared_value,
                        er.absolute_lift::float AS absolute_lift,
                        er.relative_lift::float AS relative_lift,
                        er.p_value::float AS p_value,
                        er.ci_lower::float AS ci_lower,
                        er.ci_upper::float AS ci_upper,
                        er.is_significant,
                        er.test_method
                    FROM experiment_results er
                    JOIN metrics_definitions md
                        ON md.id = er.metric_definition_id
                    JOIN experiment_variants baseline
                        ON baseline.id = er.baseline_variant_id
                    JOIN experiment_variants compared
                        ON compared.id = er.compared_variant_id
                    WHERE er.experiment_id = %s
                    ORDER BY er.calculated_at DESC, md.metric_key
                    """,
                    (experiment_id,),
                )
                rows = cursor.fetchall()

        return ExperimentSavedResultsResponse(
            experiment_id=experiment_id,
            results=[MetricResultResponse(**row) for row in rows],
        )

    def get_users_summary(self) -> UsersSummaryResponse:
        """Return compact users table summary."""
        with get_db_connection() as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    """
                    SELECT
                        COUNT(*)::int AS users_count,
                        COUNT(DISTINCT country_code)::int AS countries_count,
                        COUNT(DISTINCT device_type)::int AS device_types_count,
                        MIN(registered_at) AS first_registered_at,
                        MAX(registered_at) AS last_registered_at
                    FROM users
                    """
                )
                row = cursor.fetchone()

        return UsersSummaryResponse(**row)

    def get_events_summary(self) -> EventsSummaryResponse:
        """Return compact events table summary."""
        with get_db_connection() as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    """
                    SELECT
                        COUNT(*)::int AS events_count,
                        MIN(event_timestamp) AS first_event_at,
                        MAX(event_timestamp) AS last_event_at,
                        COALESCE(
                            SUM(event_value)
                                FILTER (
                                    WHERE event_name IN (
                                        'purchase',
                                        'subscription_start',
                                        'subscription_renewal'
                                    )
                                ),
                            0
                        )::float AS revenue_total
                    FROM events
                    """
                )
                summary_row = cursor.fetchone()
                cursor.execute(
                    """
                    SELECT event_name, COUNT(*)::int AS events_count
                    FROM events
                    GROUP BY event_name
                    ORDER BY events_count DESC, event_name
                    """
                )
                event_rows = cursor.fetchall()

        return EventsSummaryResponse(
            **summary_row,
            by_event_name=[EventCountItem(**row) for row in event_rows],
        )


class DashboardService:
    """High-level read API for experiment dashboard screens."""

    def __init__(
        self,
        repository: DashboardRepository | None = None,
        metrics_repository: MetricsRepository | None = None,
    ) -> None:
        self.repository = repository or DashboardRepository()
        self.metrics_repository = metrics_repository or MetricsRepository()

    def list_experiments(self) -> list[ExperimentListItem]:
        """Return experiments for the list page."""
        return self.repository.list_experiments()

    def get_experiment(self, experiment_id: int) -> ExperimentDetailResponse:
        """Return one experiment or raise a 404-compatible error."""
        experiment = self.repository.get_experiment(experiment_id)
        if experiment is None:
            raise ExperimentNotFoundError(f"experiment not found: {experiment_id}")
        return experiment

    def get_assignments(self, experiment_id: int) -> ExperimentAssignmentsResponse:
        """Return assignment group sizes for one experiment."""
        self.get_experiment(experiment_id)
        return self.repository.get_assignments(experiment_id)

    def get_live_metrics(self, experiment_id: int) -> ExperimentMetricsResponse:
        """Calculate metrics from current assignments and events without saving."""
        self.get_experiment(experiment_id)
        participant_rows = self.metrics_repository.fetch_participant_metrics(experiment_id)
        if not participant_rows:
            raise ExperimentValidationError("experiment has no assignments to analyze")

        results = analyze_experiment_metrics(participant_rows)
        return ExperimentMetricsResponse(
            experiment_id=experiment_id,
            results=[
                MetricResultResponse(
                    metric_key=result.metric_key,
                    metric_name=result.metric_name,
                    baseline_variant_key=result.baseline_variant_key,
                    compared_variant_key=result.compared_variant_key,
                    sample_size_baseline=result.sample_size_baseline,
                    sample_size_compared=result.sample_size_compared,
                    baseline_value=result.baseline_value,
                    compared_value=result.compared_value,
                    absolute_lift=result.absolute_lift,
                    relative_lift=result.relative_lift,
                    p_value=result.p_value,
                    ci_lower=result.ci_lower,
                    ci_upper=result.ci_upper,
                    is_significant=result.is_significant,
                    test_method=result.test_method,
                )
                for result in results
            ],
        )

    def get_saved_results(self, experiment_id: int) -> ExperimentSavedResultsResponse:
        """Return saved statistical analysis results."""
        self.get_experiment(experiment_id)
        return self.repository.get_saved_results(experiment_id)

    def get_users_summary(self) -> UsersSummaryResponse:
        """Return users summary."""
        return self.repository.get_users_summary()

    def get_events_summary(self) -> EventsSummaryResponse:
        """Return events summary."""
        return self.repository.get_events_summary()
