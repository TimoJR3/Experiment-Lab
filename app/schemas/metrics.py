"""Schemas for experiment metric analysis responses."""

from __future__ import annotations

from pydantic import BaseModel


class MetricResultResponse(BaseModel):
    """API response item for one analyzed metric."""

    metric_key: str
    metric_name: str
    baseline_variant_key: str
    compared_variant_key: str
    sample_size_baseline: int
    sample_size_compared: int
    baseline_value: float
    compared_value: float
    absolute_lift: float
    relative_lift: float | None
    p_value: float | None
    ci_lower: float | None
    ci_upper: float | None
    is_significant: bool | None
    test_method: str


class ExperimentAnalysisResponse(BaseModel):
    """API response for a full experiment analysis run."""

    experiment_key: str
    results_saved: int
    results: list[MetricResultResponse]
