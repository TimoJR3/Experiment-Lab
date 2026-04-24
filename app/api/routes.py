"""Top-level API routes for service checks and experiment operations."""

from fastapi import APIRouter, HTTPException, status

from app.schemas.health import HealthResponse
from app.schemas.experiments import (
    ExperimentAssignmentResponse,
    ExperimentCreateRequest,
    ExperimentStartRequest,
    ExperimentSummaryResponse,
)
from app.schemas.metrics import ExperimentAnalysisResponse
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
