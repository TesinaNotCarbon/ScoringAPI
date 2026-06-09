from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request, status

from core.exceptions import InvalidCellIdError, IPFSDownloadError, SatelliteDataError
from models.schemas import ChainlinkScoreResponse, ErrorResponse, HealthResponse, ScoreRequest, ScoreResponse

router = APIRouter()


@router.get("/", response_model=HealthResponse, tags=["health"])
async def health_check(request: Request) -> HealthResponse:
    settings = request.app.state.settings
    return HealthResponse(
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )


@router.get(
    "/score/{cell_id}",
    response_model=ScoreResponse,
    responses={422: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
    tags=["scoring"],
)
async def get_score(
    cell_id: str,
    request: Request,
    previous_score: int | None = Query(default=None, ge=0, le=100),
) -> ScoreResponse:
    return await _score(cell_id, request, previous_score)


@router.post(
    "/score",
    response_model=ScoreResponse,
    responses={422: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
    tags=["scoring"],
)
async def post_score(payload: ScoreRequest, request: Request) -> ScoreResponse:
    return await _score(payload.cell_id, request, payload.previous_score)


@router.get("/chainlink/score/{cell_id}", response_model=ChainlinkScoreResponse, tags=["chainlink"])
async def get_chainlink_score(
    cell_id: str,
    request: Request,
    previous_score: int | None = Query(default=None, ge=0, le=100),
) -> ChainlinkScoreResponse:
    result = await _score(cell_id, request, previous_score)
    return ChainlinkScoreResponse(
        score=result.score,
        previous_score=result.previous_score,
        score_delta=result.score_delta,
        score_trend=result.score_trend,
        review_required=result.review_required,
        flags=result.flags,
    )


async def _score(cell_id: str, request: Request, previous_score: int | None = None) -> ScoreResponse:
    try:
        return await request.app.state.scoring_service.score_cell(cell_id, previous_score)
    except InvalidCellIdError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except (IPFSDownloadError, SatelliteDataError) as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
