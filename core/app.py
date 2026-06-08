from __future__ import annotations

from contextlib import asynccontextmanager
import logging
from typing import AsyncIterator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routes import router
from core.config import Settings, get_settings
from core.exceptions import ScoringAPIError
from core.logging import configure_logging
from services.ipfs_service import IPFSService
from services.mock_ipfs_service import MockIPFSService
from services.satellite_provider import MockSatelliteImageryProvider
from services.scoring_service import ScoringService

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.settings = settings
        ipfs_service = _build_ipfs_service(settings)
        satellite_provider = MockSatelliteImageryProvider()
        app.state.ipfs_service = ipfs_service
        app.state.satellite_provider = satellite_provider
        app.state.scoring_service = ScoringService(settings, ipfs_service, satellite_provider)

        await ipfs_service.startup()
        await satellite_provider.startup()
        logger.info("Application startup completed")
        try:
            yield
        finally:
            await satellite_provider.shutdown()
            await ipfs_service.shutdown()
            logger.info("Application shutdown completed")

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type"],
        )

    app.include_router(router)

    @app.exception_handler(ScoringAPIError)
    async def scoring_error_handler(_: Request, exc: ScoringAPIError) -> JSONResponse:
        logger.warning("Handled scoring error: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc), "code": exc.__class__.__name__},
        )

    return app


def _build_ipfs_service(settings: Settings) -> IPFSService:
    if settings.environment in {"local", "test"} and not settings.pinata_jwt:
        return MockIPFSService(settings)
    return IPFSService(settings)
