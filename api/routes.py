from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from core.exceptions import InvalidCellIdError, InvalidGeoJSONError, IPFSDownloadError, SatelliteDataError
from models.schemas import ErrorResponse, HealthResponse, ScoreRequest, ScoreResponse

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
async def get_score(cell_id: str, request: Request) -> ScoreResponse:
    return await _score(cell_id, request)


@router.post(
    "/score",
    response_model=ScoreResponse,
    responses={422: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
    tags=["scoring"],
)
async def post_score(payload: ScoreRequest, request: Request) -> ScoreResponse:
    return await _score(payload.cell_id, request)


@router.get("/chainlink/score/{cell_id}", response_model=dict[str, int], tags=["chainlink"])
async def get_chainlink_score(cell_id: str, request: Request) -> dict[str, int]:
    result = await _score(cell_id, request)
    return {"score": result.score}


async def _score(cell_id: str, request: Request) -> ScoreResponse:
    try:
        return await request.app.state.scoring_service.score_cell(cell_id)
    except (InvalidCellIdError, InvalidGeoJSONError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except (IPFSDownloadError, SatelliteDataError) as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
