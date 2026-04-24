"""API tests for experiment endpoints without touching a real database."""

from datetime import datetime, timezone
from decimal import Decimal

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.experiments import ExperimentAssignmentResponse, ExperimentSummaryResponse, VariantAssignment
from app.schemas.metrics import ExperimentAnalysisResponse, MetricResultResponse
from app.services.experiment_service import ExperimentNotFoundError

client = TestClient(app)


def test_create_experiment_endpoint_returns_201(monkeypatch) -> None:
    """Experiment creation endpoint should return the created draft experiment."""

    def fake_create_experiment(payload):
        return ExperimentSummaryResponse(
            experiment_id=1,
            experiment_key=payload.experiment_key,
            name=payload.name,
            status="draft",
            created_at=datetime.now(timezone.utc),
        )

    monkeypatch.setattr("app.api.routes.experiment_service.create_experiment", fake_create_experiment)

    response = client.post(
        "/experiments",
        json={
            "experiment_key": "checkout_copy_v2",
            "name": "Checkout Copy Test",
            "variants": [
                {
                    "variant_key": "control",
                    "name": "Control",
                    "is_control": True,
                    "allocation_percent": "50",
                },
                {
                    "variant_key": "treatment",
                    "name": "Treatment",
                    "is_control": False,
                    "allocation_percent": "50",
                },
            ],
        },
    )

    assert response.status_code == 201
    assert response.json()["status"] == "draft"
    assert response.json()["experiment_key"] == "checkout_copy_v2"


def test_start_experiment_endpoint_returns_404(monkeypatch) -> None:
    """Missing experiments should map to HTTP 404."""

    def fake_start_experiment(experiment_key, payload):
        raise ExperimentNotFoundError(f"experiment not found: {experiment_key}")

    monkeypatch.setattr("app.api.routes.experiment_service.start_experiment", fake_start_experiment)

    response = client.post(
        "/experiments/missing_experiment/start",
        json={"user_ids": [1, 2, 3]},
    )

    assert response.status_code == 404


def test_start_experiment_endpoint_returns_assignments(monkeypatch) -> None:
    """Start endpoint should return deterministic assignment results."""

    def fake_start_experiment(experiment_key, payload):
        return ExperimentAssignmentResponse(
            experiment_id=7,
            experiment_key=experiment_key,
            status="running",
            assigned_users=2,
            assignments=[
                VariantAssignment(
                    user_id=1,
                    variant_id=10,
                    variant_key="control",
                    assignment_bucket=Decimal("12.345678"),
                ),
                VariantAssignment(
                    user_id=2,
                    variant_id=11,
                    variant_key="treatment",
                    assignment_bucket=Decimal("76.543210"),
                ),
            ],
        )

    monkeypatch.setattr("app.api.routes.experiment_service.start_experiment", fake_start_experiment)

    response = client.post(
        "/experiments/checkout_copy_v2/start",
        json={"user_ids": [1, 2]},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "running"
    assert response.json()["assigned_users"] == 2


def test_analyze_experiment_endpoint_returns_results(monkeypatch) -> None:
    """Analyze endpoint should return saved metric results."""

    def fake_analyze_experiment(experiment_key):
        return ExperimentAnalysisResponse(
            experiment_key=experiment_key,
            results_saved=1,
            results=[
                MetricResultResponse(
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
                    p_value=0.5,
                    ci_lower=-0.03,
                    ci_upper=0.07,
                    is_significant=False,
                    test_method="two_proportion_ztest",
                )
            ],
        )

    monkeypatch.setattr("app.api.routes.metrics_service.analyze_experiment", fake_analyze_experiment)

    response = client.post("/experiments/checkout_copy_v2/analyze")

    assert response.status_code == 200
    assert response.json()["results_saved"] == 1
    assert response.json()["results"][0]["metric_key"] == "conversion_rate"
