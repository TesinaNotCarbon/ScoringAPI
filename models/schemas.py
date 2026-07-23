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
    project_id: str = Field(..., pattern=r"^0x[a-fA-F0-9]{40}$")


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


class ProjectScoringRecord(BaseModel):
    measurement_date: int = Field(..., ge=1)
    scoring: int = Field(..., ge=0, le=100)
    fraud_scoring: int = Field(..., ge=0, le=100)
    stored_at: int = Field(..., ge=0)


class ProjectScoringAnalysisRequest(BaseModel):
    project_id: str = Field(..., pattern=r"^0x[a-fA-F0-9]{40}$")
    cell_id: str
    measurement_date: int = Field(..., ge=1)
    indicators: Indicators
    cloud_coverage: float = Field(..., ge=0.0, le=1.0)
    flags: list[str] = Field(default_factory=list)
    previous_scoring_history: list[ProjectScoringRecord] = Field(default_factory=list)


class AIScoringResponse(BaseModel):
    scoring: str = Field(..., pattern=r"^(0\.\d{2}|1\.00)$")
    fraud_scoring: str = Field(..., pattern=r"^(0\.\d{2}|1\.00)$")


class ScoreResponse(BaseModel):
    project_id: str
    cell_id: str
    scoring: str = Field(..., pattern=r"^(0\.\d{2}|1\.00)$")
    fraud_scoring: str = Field(..., pattern=r"^(0\.\d{2}|1\.00)$")
    measurement_date: int


class ChainlinkScoreResponse(BaseModel):
    project_id: str
    cell_id: str
    scoring: int = Field(..., ge=0, le=100)
    fraud_scoring: int = Field(..., ge=0, le=100)
    measurement_date: int
    schema_version: str = "chainlink-project-scoring-v1"
