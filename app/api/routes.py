"""Top-level API routes for service checks and experiment operations."""

from fastapi import APIRouter, HTTPException, status

from app.schemas.dashboard import (
    EventsSummaryResponse,
    ExperimentAssignmentsResponse,
    ExperimentDetailResponse,
    ExperimentListItem,
    ExperimentMetricsResponse,
    ExperimentSavedResultsResponse,
    UsersSummaryResponse,
)
from app.schemas.experiments import (
    ExperimentAssignmentResponse,
    ExperimentCreateRequest,
    ExperimentStartRequest,
    ExperimentSummaryResponse,
)
from app.schemas.health import HealthResponse
from app.schemas.metrics import ExperimentAnalysisResponse
from app.services.dashboard_service import DashboardService
from app.services.experiment_service import (
    ExperimentNotFoundError,
    ExperimentService,
    ExperimentStatusError,
    ExperimentValidationError,
)
from app.services.metrics_service import MetricsService

router = APIRouter()
experiment_service = ExperimentService()
metrics_service = MetricsService()
dashboard_service = DashboardService()


@router.get("/health", response_model=HealthResponse, tags=["health"])
def healthcheck() -> HealthResponse:
    """Return a simple service health response."""
    return HealthResponse(status="ok")


@router.post(
    "/experiments",
    response_model=ExperimentSummaryResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["experiments"],
)
def create_experiment(payload: ExperimentCreateRequest) -> ExperimentSummaryResponse:
    """Create a draft experiment with its variants."""
    try:
        return experiment_service.create_experiment(payload)
    except ExperimentValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/experiments", response_model=list[ExperimentListItem], tags=["experiments"])
def list_experiments() -> list[ExperimentListItem]:
    """Return experiments for dashboard navigation."""
    return dashboard_service.list_experiments()


@router.get(
    "/experiments/{experiment_id}",
    response_model=ExperimentDetailResponse,
    tags=["experiments"],
)
def get_experiment(experiment_id: int) -> ExperimentDetailResponse:
    """Return experiment details by numeric id."""
    try:
        return dashboard_service.get_experiment(experiment_id)
    except ExperimentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/experiments/{experiment_id}/assignments",
    response_model=ExperimentAssignmentsResponse,
    tags=["experiments"],
)
def get_experiment_assignments(experiment_id: int) -> ExperimentAssignmentsResponse:
    """Return assignment group sizes for one experiment."""
    try:
        return dashboard_service.get_assignments(experiment_id)
    except ExperimentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/experiments/{experiment_id}/metrics",
    response_model=ExperimentMetricsResponse,
    tags=["experiments"],
)
def get_experiment_metrics(experiment_id: int) -> ExperimentMetricsResponse:
    """Return live metric calculations for one experiment."""
    try:
        return dashboard_service.get_live_metrics(experiment_id)
    except ExperimentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ExperimentValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/experiments/{experiment_id}/results",
    response_model=ExperimentSavedResultsResponse,
    tags=["experiments"],
)
def get_experiment_results(experiment_id: int) -> ExperimentSavedResultsResponse:
    """Return saved analysis results for one experiment."""
    try:
        return dashboard_service.get_saved_results(experiment_id)
    except ExperimentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/experiments/{experiment_key}/start",
    response_model=ExperimentAssignmentResponse,
    tags=["experiments"],
)
def start_experiment(
    experiment_key: str,
    payload: ExperimentStartRequest,
) -> ExperimentAssignmentResponse:
    """Start an experiment and persist deterministic assignments."""
    try:
        return experiment_service.start_experiment(experiment_key=experiment_key, payload=payload)
    except ExperimentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ExperimentStatusError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ExperimentValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/users/summary", response_model=UsersSummaryResponse, tags=["summary"])
def get_users_summary() -> UsersSummaryResponse:
    """Return a compact user table summary."""
    return dashboard_service.get_users_summary()


@router.get("/events/summary", response_model=EventsSummaryResponse, tags=["summary"])
def get_events_summary() -> EventsSummaryResponse:
    """Return a compact event table summary."""
    return dashboard_service.get_events_summary()


@router.post(
    "/experiments/{experiment_key}/analyze",
    response_model=ExperimentAnalysisResponse,
    tags=["experiments"],
)
def analyze_experiment(experiment_key: str) -> ExperimentAnalysisResponse:
    """Calculate metrics, run statistical tests, and save analysis results."""
    try:
        return metrics_service.analyze_experiment(experiment_key=experiment_key)
    except ExperimentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ExperimentStatusError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ExperimentValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
