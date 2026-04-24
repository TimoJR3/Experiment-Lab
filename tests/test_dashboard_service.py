"""Tests for dashboard read service orchestration."""

from app.experiments.metrics import ParticipantMetrics
from app.schemas.dashboard import (
    AssignmentGroupSummary,
    ExperimentAssignmentsResponse,
    ExperimentDetailResponse,
    ExperimentListItem,
    ExperimentSavedResultsResponse,
)
from app.services.dashboard_service import DashboardService
from app.services.experiment_service import ExperimentNotFoundError


class FakeDashboardRepository:
    """In-memory repository for dashboard service tests."""

    def __init__(self, has_experiment: bool = True) -> None:
        self.has_experiment = has_experiment

    def list_experiments(self):
        return [
            ExperimentListItem(
                id=1,
                experiment_key="checkout_v2",
                name="Checkout Test",
                status="running",
                start_at=None,
                end_at=None,
                variants_count=2,
                assignments_count=4,
            )
        ]

    def get_experiment(self, experiment_id):
        if not self.has_experiment:
            return None
        return ExperimentDetailResponse(
            id=experiment_id,
            experiment_key="checkout_v2",
            name="Checkout Test",
            description=None,
            hypothesis=None,
            status="running",
            start_at=None,
            end_at=None,
            owner_name=None,
            primary_metric_key="conversion_rate",
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:00:00+00:00",
        )

    def get_assignments(self, experiment_id):
        return ExperimentAssignmentsResponse(
            experiment_id=experiment_id,
            total_assigned=4,
            groups=[
                AssignmentGroupSummary(variant_id=10, variant_key="control", is_control=True, users_count=2),
                AssignmentGroupSummary(variant_id=20, variant_key="treatment", is_control=False, users_count=2),
            ],
        )

    def get_saved_results(self, experiment_id):
        return ExperimentSavedResultsResponse(experiment_id=experiment_id, results=[])


class FakeMetricsRepository:
    """In-memory metrics repository for live metrics tests."""

    def fetch_participant_metrics(self, experiment_id):
        return [
            ParticipantMetrics(1, 10, "control", 1, 100.0, (100.0,)),
            ParticipantMetrics(2, 10, "control", 0, 0.0, ()),
            ParticipantMetrics(3, 20, "treatment", 1, 120.0, (120.0,)),
            ParticipantMetrics(4, 20, "treatment", 1, 80.0, (80.0,)),
        ]


def test_dashboard_service_returns_live_metrics() -> None:
    """Dashboard service should calculate live metrics through the metrics engine."""
    service = DashboardService(
        repository=FakeDashboardRepository(),
        metrics_repository=FakeMetricsRepository(),
    )

    response = service.get_live_metrics(1)

    assert response.experiment_id == 1
    assert len(response.results) == 4
    assert {item.metric_key for item in response.results} == {
        "conversion_rate",
        "average_revenue_per_user",
        "average_order_value",
        "purchase_rate",
    }


def test_dashboard_service_raises_for_missing_experiment() -> None:
    """Dashboard service should raise a domain error for unknown experiments."""
    service = DashboardService(
        repository=FakeDashboardRepository(has_experiment=False),
        metrics_repository=FakeMetricsRepository(),
    )

    try:
        service.get_experiment(999)
    except ExperimentNotFoundError as exc:
        assert "999" in str(exc)
    else:
        raise AssertionError("ExperimentNotFoundError was not raised")
