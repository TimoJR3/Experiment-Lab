"""Tests for metrics service orchestration."""

import pytest

from app.experiments.metrics import ParticipantMetrics
from app.services.experiment_service import ExperimentStatusError
from app.services.metrics_service import MetricsService


class FakeMetricsRepository:
    """Small fake repository for service tests."""

    def __init__(self, experiment_status: str = "running") -> None:
        self.experiment_status = experiment_status
        self.saved_results = []

    def get_experiment(self, experiment_key: str):
        return {
            "id": 1,
            "experiment_key": experiment_key,
            "status": self.experiment_status,
        }

    def fetch_participant_metrics(self, experiment_id: int):
        return [
            ParticipantMetrics(1, 10, "control", 1, 100.0, (100.0,)),
            ParticipantMetrics(2, 10, "control", 0, 0.0, ()),
            ParticipantMetrics(3, 20, "treatment", 1, 120.0, (120.0,)),
            ParticipantMetrics(4, 20, "treatment", 1, 80.0, (80.0,)),
        ]

    def ensure_metric_definitions(self):
        return {
            "conversion_rate": 1,
            "average_revenue_per_user": 2,
            "average_order_value": 3,
            "purchase_rate": 4,
        }

    def save_results(self, experiment_id, results, metric_ids):
        self.saved_results = results


def test_metrics_service_saves_analysis_results() -> None:
    """Metrics service should calculate and persist all supported metrics."""
    repository = FakeMetricsRepository()
    service = MetricsService(repository=repository)

    response = service.analyze_experiment("checkout_v2")

    assert response.experiment_key == "checkout_v2"
    assert response.results_saved == 4
    assert len(repository.saved_results) == 4


def test_metrics_service_rejects_draft_experiment() -> None:
    """Draft experiments should not be analyzed."""
    service = MetricsService(repository=FakeMetricsRepository(experiment_status="draft"))

    with pytest.raises(ExperimentStatusError):
        service.analyze_experiment("checkout_v2")
