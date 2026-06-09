from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ScoreStatus(str, Enum):
    APPROVED = "approved"
    REVIEW = "review"
    REJECTED = "rejected"


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str
    version: str
    environment: str


class ErrorResponse(BaseModel):
    detail: str
    code: str


class ScoreRequest(BaseModel):
    cell_id: str = Field(..., min_length=3, max_length=128, pattern=r"^[a-zA-Z0-9._:-]+$")
    previous_score: int | None = Field(default=None, ge=0, le=100)


class ProjectGeometry(BaseModel):
    cell_id: str
    geojson: dict[str, Any]


class SatelliteObservation(BaseModel):
    model_config = ConfigDict(frozen=True)

    nir: float = Field(..., ge=0.0, le=1.0)
    red: float = Field(..., ge=0.0, le=1.0)
    blue: float = Field(..., ge=0.0, le=1.0)
    swir: float = Field(..., ge=0.0, le=1.0)
    timestamp: str
    cloud_coverage: float = Field(default=0.0, ge=0.0, le=1.0)


class Indicators(BaseModel):
    ndvi: float
    savi: float
    evi: float
    nbr: float


class ScoreResponse(BaseModel):
    cell_id: str
    score: int = Field(..., ge=0, le=100)
    previous_score: int | None = Field(default=None, ge=0, le=100)
    score_delta: int | None = None
    score_trend: str = "no_baseline"
    status: ScoreStatus
    indicators: Indicators
    flags: list[str] = Field(default_factory=list)
    review_required: bool


class ChainlinkScoreResponse(BaseModel):
    score: int = Field(..., ge=0, le=100)
    previous_score: int | None = Field(default=None, ge=0, le=100)
    score_delta: int | None = None
    score_trend: str
    review_required: bool
    flags: list[str] = Field(default_factory=list)
