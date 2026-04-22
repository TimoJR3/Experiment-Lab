"""Top-level API routes for service checks."""

from fastapi import APIRouter

from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["health"])
def healthcheck() -> HealthResponse:
    """Return a simple service health response."""
    return HealthResponse(status="ok")
