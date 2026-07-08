from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CriticalityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


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
    measurement_date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")


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


class FraudAnalysis(BaseModel):
    criticality: CriticalityLevel
    description: str = Field(..., min_length=1)


class FraudAnalysisRequest(BaseModel):
    cell_id: str
    score: int = Field(..., ge=0, le=100)
    previous_score: int | None = Field(default=None, ge=0, le=100)
    score_delta: int | None = None
    score_trend: str = "no_baseline"
    measurement_date: str | None = None
    indicators: Indicators
    flags: list[str] = Field(default_factory=list)


class ScoreResponse(BaseModel):
    score: int = Field(..., ge=0, le=100)
    criticality: CriticalityLevel
    description: str
    measurement_date: str | None = None


class ChainlinkScoreResponse(BaseModel):
    cell_id: str
    score: int = Field(..., ge=0, le=100)
    criticality: CriticalityLevel
    criticality_code: int = Field(..., ge=0, le=2, description="0=low, 1=medium, 2=high")
    decision: str = Field(..., description="approve, review, or reject")
    flags: list[str] = Field(default_factory=list)
    measurement_date: str | None = None
    schema_version: str = "chainlink-score-v1"
