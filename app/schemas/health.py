"""Response schemas for service health endpoints."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Schema for the `/health` endpoint."""

    status: str
