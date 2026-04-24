"""API tests for read-only dashboard endpoints."""

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app
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

client = TestClient(app)


def _metric_result() -> MetricResultResponse:
    """Build one metric response row for endpoint tests."""
    return MetricResultResponse(
        metric_key="conversion_rate",
        metric_name="Conversion Rate",
        baseline_variant_key="control",
        compared_variant_key="treatment",
        sample_size_baseline=100,
        sample_size_compared=100,
        baseline_value=0.1,
        compared_value=0.12,
        absolute_lift=0.02,
        relative_lift=0.2,
        p_value=0.4,
        ci_lower=-0.03,
        ci_upper=0.07,
        is_significant=False,
        test_method="two_proportion_ztest",
    )


def test_list_experiments_endpoint(monkeypatch) -> None:
    """Experiments endpoint should return dashboard list items."""

    def fake_list_experiments():
        return [
            ExperimentListItem(
                id=1,
                experiment_key="checkout_v2",
                name="Checkout Test",
                status="running",
                start_at=None,
                end_at=None,
                variants_count=2,
                assignments_count=200,
            )
        ]

    monkeypatch.setattr("app.api.routes.dashboard_service.list_experiments", fake_list_experiments)

    response = client.get("/experiments")

    assert response.status_code == 200
    assert response.json()[0]["experiment_key"] == "checkout_v2"


def test_get_experiment_detail_endpoint(monkeypatch) -> None:
    """Experiment detail endpoint should return one experiment by id."""

    def fake_get_experiment(experiment_id):
        return ExperimentDetailResponse(
            id=experiment_id,
            experiment_key="checkout_v2",
            name="Checkout Test",
            description=None,
            hypothesis="New copy improves purchase conversion.",
            status="running",
            start_at=None,
            end_at=None,
            owner_name="Ahmed",
            primary_metric_key="conversion_rate",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    monkeypatch.setattr("app.api.routes.dashboard_service.get_experiment", fake_get_experiment)

    response = client.get("/experiments/1")

    assert response.status_code == 200
    assert response.json()["id"] == 1


def test_assignment_metrics_and_results_endpoints(monkeypatch) -> None:
    """Dashboard experiment subresources should return assignment and analysis data."""

    def fake_get_assignments(experiment_id):
        return ExperimentAssignmentsResponse(
            experiment_id=experiment_id,
            total_assigned=200,
            groups=[
                AssignmentGroupSummary(
                    variant_id=10,
                    variant_key="control",
                    is_control=True,
                    users_count=100,
                ),
                AssignmentGroupSummary(
                    variant_id=11,
                    variant_key="treatment",
                    is_control=False,
                    users_count=100,
                ),
            ],
        )

    def fake_get_live_metrics(experiment_id):
        return ExperimentMetricsResponse(experiment_id=experiment_id, results=[_metric_result()])

    def fake_get_saved_results(experiment_id):
        return ExperimentSavedResultsResponse(experiment_id=experiment_id, results=[_metric_result()])

    monkeypatch.setattr("app.api.routes.dashboard_service.get_assignments", fake_get_assignments)
    monkeypatch.setattr("app.api.routes.dashboard_service.get_live_metrics", fake_get_live_metrics)
    monkeypatch.setattr("app.api.routes.dashboard_service.get_saved_results", fake_get_saved_results)

    assignments = client.get("/experiments/1/assignments")
    metrics = client.get("/experiments/1/metrics")
    results = client.get("/experiments/1/results")

    assert assignments.status_code == 200
    assert assignments.json()["total_assigned"] == 200
    assert metrics.status_code == 200
    assert metrics.json()["results"][0]["metric_key"] == "conversion_rate"
    assert results.status_code == 200
    assert results.json()["results"][0]["test_method"] == "two_proportion_ztest"


def test_global_summary_endpoints(monkeypatch) -> None:
    """Global summary endpoints should return compact users/events state."""

    def fake_get_users_summary():
        return UsersSummaryResponse(
            users_count=250,
            countries_count=4,
            device_types_count=3,
            first_registered_at=None,
            last_registered_at=None,
        )

    def fake_get_events_summary():
        return EventsSummaryResponse(
            events_count=1000,
            first_event_at=None,
            last_event_at=None,
            revenue_total=1234.5,
            by_event_name=[
                EventCountItem(event_name="app_open", events_count=600),
                EventCountItem(event_name="purchase", events_count=50),
            ],
        )

    monkeypatch.setattr("app.api.routes.dashboard_service.get_users_summary", fake_get_users_summary)
    monkeypatch.setattr("app.api.routes.dashboard_service.get_events_summary", fake_get_events_summary)

    users = client.get("/users/summary")
    events = client.get("/events/summary")

    assert users.status_code == 200
    assert users.json()["users_count"] == 250
    assert events.status_code == 200
    assert events.json()["revenue_total"] == 1234.5
