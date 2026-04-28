"""Prepare a reproducible Docker demo dataset for Experiment Lab."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.db.ingest_events import ingest_dataset
from app.db.session import get_db_connection
from app.experiments.synthetic_data import GenerationConfig, generate_dataset
from app.schemas.experiments import (
    ExperimentCreateRequest,
    ExperimentStartRequest,
    ExperimentVariantInput,
)
from app.services.experiment_service import (
    ExperimentService,
    ExperimentStatusError,
    ExperimentValidationError,
)
from app.services.metrics_service import MetricsService

DEMO_EXPERIMENT_KEY = "big_data_checkout_test"
DEMO_USERS_COUNT = 10_000
DEMO_DAYS = 180
DEMO_SEED = 42

DASHBOARD_URL = "http://localhost:8501"
SWAGGER_URL = "http://localhost:8000/docs"


@dataclass(frozen=True, slots=True)
class DemoSummary:
    """Final state of the prepared demo dataset."""

    users_count: int
    events_count: int
    experiment_key: str
    assigned_users: int
    analysis_completed: bool


def _count_rows(table_name: str) -> int:
    """Count rows in a known project table."""
    allowed_tables = {
        "users",
        "events",
        "experiment_assignments",
        "experiment_results",
    }
    if table_name not in allowed_tables:
        raise ValueError(f"unsupported table for counting: {table_name}")

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            return int(cursor.fetchone()[0])


def _count_demo_assignments() -> int:
    """Count users assigned to the demo experiment."""
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM experiment_assignments ea
                JOIN experiments e
                    ON e.id = ea.experiment_id
                WHERE e.experiment_key = %s
                """,
                (DEMO_EXPERIMENT_KEY,),
            )
            return int(cursor.fetchone()[0])


def _count_demo_results() -> int:
    """Count saved analysis rows for the demo experiment."""
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM experiment_results er
                JOIN experiments e
                    ON e.id = er.experiment_id
                WHERE e.experiment_key = %s
                """,
                (DEMO_EXPERIMENT_KEY,),
            )
            return int(cursor.fetchone()[0])


def _load_demo_user_ids(limit: int = DEMO_USERS_COUNT) -> list[int]:
    """Load deterministic user ids for the demo assignment."""
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id
                FROM users
                ORDER BY id
                LIMIT %s
                """,
                (limit,),
            )
            return [int(row[0]) for row in cursor.fetchall()]


def _ensure_demo_data() -> None:
    """Generate deterministic synthetic users/events when the dataset is small."""
    users_count = _count_rows("users")
    events_count = _count_rows("events")
    if users_count >= DEMO_USERS_COUNT and events_count >= DEMO_USERS_COUNT:
        return

    dataset = generate_dataset(
        GenerationConfig(
            users_count=DEMO_USERS_COUNT,
            days=DEMO_DAYS,
            seed=DEMO_SEED,
        )
    )
    ingest_dataset(dataset)


def _demo_experiment_payload() -> ExperimentCreateRequest:
    """Build the reusable demo experiment payload."""
    return ExperimentCreateRequest(
        experiment_key=DEMO_EXPERIMENT_KEY,
        name="Большой A/B тест checkout",
        description="Демо-эксперимент на большом synthetic event log.",
        hypothesis="Новая версия checkout повышает конверсию в покупку.",
        owner_name="Ahmed",
        primary_metric_key="conversion_rate",
        variants=[
            ExperimentVariantInput(
                variant_key="control",
                name="Контроль",
                description="Текущая версия checkout.",
                is_control=True,
                allocation_percent=Decimal("50"),
            ),
            ExperimentVariantInput(
                variant_key="treatment",
                name="Тестовый вариант",
                description="Новая версия checkout.",
                is_control=False,
                allocation_percent=Decimal("50"),
            ),
        ],
    )


def _ensure_demo_experiment(service: ExperimentService) -> None:
    """Create the demo experiment once, then reuse it on later runs."""
    if service.repository.get_experiment(DEMO_EXPERIMENT_KEY) is not None:
        return
    service.create_experiment(_demo_experiment_payload())


def _align_assignment_window() -> None:
    """Move demo assignments to the event window for meaningful analysis.

    The event generator creates historical events. During a demo setup, users
    are assigned after data generation, so the metrics query would otherwise
    ignore all historical purchases. Backdating only the demo experiment keeps
    the service logic intact while making the reproducible demo useful.
    """
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                WITH first_event AS (
                    SELECT MIN(event_timestamp) AS assigned_at
                    FROM events
                )
                UPDATE experiment_assignments ea
                SET assigned_at = first_event.assigned_at
                FROM experiments e, first_event
                WHERE e.id = ea.experiment_id
                  AND e.experiment_key = %s
                  AND first_event.assigned_at IS NOT NULL
                """,
                (DEMO_EXPERIMENT_KEY,),
            )
        connection.commit()


def _ensure_assignments(service: ExperimentService) -> int:
    """Assign up to DEMO_USERS_COUNT users through ExperimentService."""
    user_ids = _load_demo_user_ids()
    if not user_ids:
        raise RuntimeError("В базе нет пользователей для назначения в эксперимент.")

    payload = ExperimentStartRequest(user_ids=user_ids, assignment_source="hash")
    try:
        service.start_experiment(DEMO_EXPERIMENT_KEY, payload)
    except (ExperimentStatusError, ExperimentValidationError) as exc:
        message = str(exc)
        if "completed experiments cannot receive new assignments" not in message:
            raise

    _align_assignment_window()
    return _count_demo_assignments()


def _ensure_analysis() -> bool:
    """Run analysis once, or reuse existing saved results."""
    if _count_demo_results() > 0:
        return True

    MetricsService().analyze_experiment(DEMO_EXPERIMENT_KEY)
    return _count_demo_results() > 0


def prepare_demo() -> DemoSummary:
    """Prepare data, experiment assignment, and saved analysis results."""
    _ensure_demo_data()

    experiment_service = ExperimentService()
    _ensure_demo_experiment(experiment_service)
    assigned_users = _ensure_assignments(experiment_service)
    analysis_completed = _ensure_analysis()

    return DemoSummary(
        users_count=_count_rows("users"),
        events_count=_count_rows("events"),
        experiment_key=DEMO_EXPERIMENT_KEY,
        assigned_users=assigned_users,
        analysis_completed=analysis_completed,
    )


def print_summary(summary: DemoSummary) -> None:
    """Print a concise Russian summary for Docker users."""
    analysis_status = "Анализ выполнен." if summary.analysis_completed else "Анализ не выполнен."
    print("Демо-данные готовы.")
    print(f"Пользователей: {summary.users_count}")
    print(f"Событий: {summary.events_count}")
    print(f"Эксперимент: {summary.experiment_key}")
    print(f"Назначено пользователей: {summary.assigned_users}")
    print(analysis_status)
    print()
    print("Откройте:")
    print(f"Dashboard: {DASHBOARD_URL}")
    print(f"Swagger: {SWAGGER_URL}")


def main() -> None:
    """CLI entrypoint for `python -m app.db.prepare_demo`."""
    print_summary(prepare_demo())


if __name__ == "__main__":
    main()
