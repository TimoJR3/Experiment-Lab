"""Schemas for read-only API endpoints used by the Streamlit dashboard."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.metrics import MetricResultResponse


class ExperimentListItem(BaseModel):
    """Compact experiment item for dashboard lists."""

    id: int
    experiment_key: str
    name: str
    status: str
    start_at: datetime | None
    end_at: datetime | None
    variants_count: int
    assignments_count: int


class ExperimentDetailResponse(BaseModel):
    """Detailed experiment card for the dashboard."""

    id: int
    experiment_key: str
    name: str
    description: str | None
    hypothesis: str | None
    status: str
    start_at: datetime | None
    end_at: datetime | None
    owner_name: str | None
    primary_metric_key: str | None
    created_at: datetime
    updated_at: datetime


class AssignmentGroupSummary(BaseModel):
    """Assignment counts by experiment variant."""

    variant_id: int
    variant_key: str
    is_control: bool
    users_count: int


class ExperimentAssignmentsResponse(BaseModel):
    """Assignment summary for one experiment."""

    experiment_id: int
    total_assigned: int
    groups: list[AssignmentGroupSummary]


class ExperimentMetricsResponse(BaseModel):
    """Live metric calculation response for one experiment."""

    experiment_id: int
    results: list[MetricResultResponse]


class ExperimentSavedResultsResponse(BaseModel):
    """Saved analysis results loaded from experiment_results."""

    experiment_id: int
    results: list[MetricResultResponse]


class UsersSummaryResponse(BaseModel):
    """User table summary for dashboard health checks."""

    users_count: int
    countries_count: int
    device_types_count: int
    first_registered_at: datetime | None
    last_registered_at: datetime | None


class EventCountItem(BaseModel):
    """Event count by event_name."""

    event_name: str
    events_count: int


class EventsSummaryResponse(BaseModel):
    """Event table summary for dashboard health checks."""

    events_count: int
    first_event_at: datetime | None
    last_event_at: datetime | None
    revenue_total: float
    by_event_name: list[EventCountItem]
