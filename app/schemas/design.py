"""Schemas for experiment design endpoints."""

from pydantic import BaseModel, Field


class SampleSizeRequest(BaseModel):
    """Input for sample size planning of a conversion metric."""

    baseline_rate: float = Field(gt=0, lt=1, examples=[0.134])
    mde_relative: float = Field(examples=[0.05])
    alpha: float = Field(default=0.05, gt=0, lt=1)
    power: float = Field(default=0.8, gt=0, lt=1)
    treatment_ratio: float = Field(default=1.0, gt=0)


class SampleSizeResponse(BaseModel):
    """Required users per group and in total."""

    baseline_rate: float
    expected_rate: float
    mde_absolute: float
    mde_relative: float
    alpha: float
    power: float
    users_control: int
    users_treatment: int
    users_total: int


class SrmRequest(BaseModel):
    """Observed group sizes and optional planned shares."""

    observed: dict[str, int] = Field(examples=[{"control": 10000, "treatment": 10600}])
    expected_shares: dict[str, float] | None = None
    threshold: float = Field(default=0.001, gt=0, lt=1)


class SrmResponse(BaseModel):
    """Result of the sample ratio mismatch check."""

    chi_square: float
    p_value: float
    threshold: float
    has_mismatch: bool
