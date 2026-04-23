"""API tests for experiment endpoints without touching a real database."""

from datetime import datetime, timezone
from decimal import Decimal

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.experiments import ExperimentAssignmentResponse, ExperimentSummaryResponse, VariantAssignment
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
