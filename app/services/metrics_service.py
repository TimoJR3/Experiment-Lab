"""Service layer for experiment metric calculation and result persistence."""

from __future__ import annotations

from decimal import Decimal

from psycopg.rows import dict_row
from psycopg.types.json import Json

from app.db.session import get_db_connection
from app.experiments.metrics import (
    SUPPORTED_METRICS,
    MetricAnalysisResult,
    ParticipantMetrics,
    analyze_experiment_metrics,
)
from app.schemas.metrics import ExperimentAnalysisResponse, MetricResultResponse
from app.services.experiment_service import (
    ExperimentNotFoundError,
    ExperimentStatusError,
    ExperimentValidationError,
)


class MetricsRepository:
    """PostgreSQL access for experiment analysis."""

    def get_experiment(self, experiment_key: str) -> dict | None:
        """Fetch experiment metadata needed for analysis."""
        with get_db_connection() as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    """
                    SELECT id, experiment_key, status
                    FROM experiments
                    WHERE experiment_key = %s
                    """,
                    (experiment_key,),
                )
                return cursor.fetchone()

    def fetch_participant_metrics(self, experiment_id: int) -> list[ParticipantMetrics]:
        """Load user-level purchase aggregates for assigned experiment users."""
        with get_db_connection() as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    """
                    SELECT
                        a.user_id,
                        v.id AS variant_id,
                        v.variant_key,
                        COALESCE(
                            COUNT(e.id) FILTER (WHERE e.event_name = 'purchase'),
                            0
                        )::int AS purchase_count,
                        COALESCE(
                            SUM(e.event_value) FILTER (WHERE e.event_name = 'purchase'),
                            0
                        )::float AS revenue,
                        COALESCE(
                            array_agg(e.event_value)
                                FILTER (
                                    WHERE e.event_name = 'purchase'
                                      AND e.event_value IS NOT NULL
                                ),
                            ARRAY[]::numeric[]
                        ) AS order_values
                    FROM experiment_assignments a
                    JOIN experiment_variants v
                        ON v.id = a.variant_id
                    LEFT JOIN events e
                        ON e.user_id = a.user_id
                       AND e.event_timestamp >= a.assigned_at
                    WHERE a.experiment_id = %s
                    GROUP BY a.user_id, v.id, v.variant_key
                    ORDER BY v.variant_key, a.user_id
                    """,
                    (experiment_id,),
                )
                rows = cursor.fetchall()

        return [
            ParticipantMetrics(
                user_id=row["user_id"],
                variant_id=row["variant_id"],
                variant_key=row["variant_key"],
                purchase_count=row["purchase_count"],
                revenue=float(row["revenue"] or 0),
                order_values=tuple(float(value) for value in row["order_values"]),
            )
            for row in rows
        ]

    def ensure_metric_definitions(self) -> dict[str, int]:
        """Upsert supported metrics into metrics_definitions and return ids."""
        metric_rows = [
            (
                metric_key,
                metric_info["metric_name"],
                metric_info["description"],
                metric_info["metric_type"],
                metric_info["source_event_name"],
                "user",
                "event_value" if metric_key != "conversion_rate" else "none",
                Json({"stage": "metrics_engine_v1"}),
            )
            for metric_key, metric_info in SUPPORTED_METRICS.items()
        ]

        with get_db_connection() as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.executemany(
                    """
                    INSERT INTO metrics_definitions (
                        metric_key,
                        metric_name,
                        description,
                        metric_type,
                        source_event_name,
                        aggregation_level,
                        value_column,
                        metadata
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (metric_key) DO UPDATE
                    SET
                        metric_name = EXCLUDED.metric_name,
                        description = EXCLUDED.description,
                        metric_type = EXCLUDED.metric_type,
                        source_event_name = EXCLUDED.source_event_name,
                        aggregation_level = EXCLUDED.aggregation_level,
                        value_column = EXCLUDED.value_column,
                        metadata = EXCLUDED.metadata
                    """,
                    metric_rows,
                )
                cursor.execute(
                    """
                    SELECT id, metric_key
                    FROM metrics_definitions
                    WHERE metric_key = ANY(%s)
                    """,
                    (list(SUPPORTED_METRICS.keys()),),
                )
                rows = cursor.fetchall()
            connection.commit()

        return {row["metric_key"]: row["id"] for row in rows}

    def save_results(
        self,
        experiment_id: int,
        results: list[MetricAnalysisResult],
        metric_ids: dict[str, int],
    ) -> None:
        """Persist analysis results into experiment_results."""
        rows = [
            (
                experiment_id,
                metric_ids[result.metric_key],
                result.baseline_variant_id,
                result.compared_variant_id,
                result.sample_size_baseline,
                result.sample_size_compared,
                Decimal(str(result.baseline_value)),
                Decimal(str(result.compared_value)),
                Decimal(str(result.absolute_lift)),
                None if result.relative_lift is None else Decimal(str(result.relative_lift)),
                None if result.p_value is None else Decimal(str(result.p_value)),
                None if result.ci_lower is None else Decimal(str(result.ci_lower)),
                None if result.ci_upper is None else Decimal(str(result.ci_upper)),
                result.is_significant,
                result.test_method,
                Json(result.result_payload),
            )
            for result in results
        ]

        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.executemany(
                    """
                    INSERT INTO experiment_results (
                        experiment_id,
                        metric_definition_id,
                        baseline_variant_id,
                        compared_variant_id,
                        sample_size_baseline,
                        sample_size_compared,
                        baseline_value,
                        compared_value,
                        absolute_lift,
                        relative_lift,
                        p_value,
                        ci_lower,
                        ci_upper,
                        is_significant,
                        test_method,
                        result_payload
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    rows,
                )
            connection.commit()


class MetricsService:
    """Run experiment metric analysis and save the results."""

    def __init__(self, repository: MetricsRepository | None = None) -> None:
        self.repository = repository or MetricsRepository()

    def analyze_experiment(self, experiment_key: str) -> ExperimentAnalysisResponse:
        """Calculate supported metrics for one experiment."""
        experiment = self.repository.get_experiment(experiment_key)
        if experiment is None:
            raise ExperimentNotFoundError(f"experiment not found: {experiment_key}")

        if experiment["status"] == "draft":
            raise ExperimentStatusError("draft experiments cannot be analyzed")

        participant_rows = self.repository.fetch_participant_metrics(experiment["id"])
        if not participant_rows:
            raise ExperimentValidationError("experiment has no assignments to analyze")

        results = analyze_experiment_metrics(participant_rows)
        metric_ids = self.repository.ensure_metric_definitions()
        self.repository.save_results(
            experiment_id=experiment["id"],
            results=results,
            metric_ids=metric_ids,
        )

        return ExperimentAnalysisResponse(
            experiment_key=experiment_key,
            results_saved=len(results),
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
