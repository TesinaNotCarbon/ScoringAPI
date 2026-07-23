from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Request, status

from core.exceptions import AIProviderError, BlockchainAdapterError, InvalidCellIdError, IPFSDownloadError, SatelliteDataError
from models.schemas import ChainlinkScoreResponse, ErrorResponse, HealthResponse, ScoreRequest, ScoreResponse

router = APIRouter()

ProjectIdPath = Annotated[str, Path(pattern=r"^0x[a-fA-F0-9]{40}$")]


@router.get("/", response_model=HealthResponse, tags=["health"])
async def health_check(request: Request) -> HealthResponse:
    settings = request.app.state.settings
    return HealthResponse(
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )


@router.get(
    "/score/{project_id}",
    response_model=ScoreResponse,
    responses={422: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
    tags=["scoring"],
)
async def get_score(project_id: ProjectIdPath, request: Request) -> ScoreResponse:
    return await _score(project_id, request)


@router.post(
    "/score",
    response_model=ScoreResponse,
    responses={422: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
    tags=["scoring"],
)
async def post_score(payload: ScoreRequest, request: Request) -> ScoreResponse:
    return await _score(payload.project_id, request)


@router.get("/chainlink/score/{project_id}", response_model=ChainlinkScoreResponse, tags=["chainlink"])
async def get_chainlink_score(project_id: ProjectIdPath, request: Request) -> ChainlinkScoreResponse:
    try:
        return await request.app.state.scoring_service.score_project_for_consensus(project_id)
    except (InvalidCellIdError, BlockchainAdapterError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except (IPFSDownloadError, SatelliteDataError, AIProviderError) as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


async def _score(project_id: str, request: Request) -> ScoreResponse:
    try:
        return await request.app.state.scoring_service.score_project(project_id)
    except (InvalidCellIdError, BlockchainAdapterError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except (IPFSDownloadError, SatelliteDataError, AIProviderError) as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
