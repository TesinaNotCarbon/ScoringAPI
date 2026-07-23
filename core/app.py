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
from adapters.ai import GroqAIProvider
from adapters.blockchain import MockProjectManagerAdapter, ProjectManagerAdapter, ProjectManagerClient
from adapters.ipfs import IPFSService
from adapters.ipfs.mocks import MockIPFSService
from adapters.satellite import HTTPSatelliteImageryProvider, MockSatelliteImageryProvider
from services.scoring_service import ScoringService

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.settings = settings
        ipfs_service = _build_ipfs_service(settings)
        satellite_provider = _build_satellite_provider(settings)
        ai_provider = _build_ai_provider(settings)
        project_manager = _build_project_manager(settings)
        app.state.ipfs_service = ipfs_service
        app.state.satellite_provider = satellite_provider
        app.state.ai_provider = ai_provider
        app.state.project_manager = project_manager
        app.state.scoring_service = ScoringService(settings, ipfs_service, satellite_provider, ai_provider, project_manager)

        await ipfs_service.startup()
        await satellite_provider.startup()
        await ai_provider.startup()
        await project_manager.startup()
        logger.info("Application startup completed")
        try:
            yield
        finally:
            await project_manager.shutdown()
            await ai_provider.shutdown()
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


def _build_satellite_provider(settings: Settings) -> MockSatelliteImageryProvider | HTTPSatelliteImageryProvider:
    if settings.satellite_provider == "http":
        return HTTPSatelliteImageryProvider(settings)
    return MockSatelliteImageryProvider()


def _build_ai_provider(settings: Settings) -> GroqAIProvider:
    return GroqAIProvider(settings)


def _build_project_manager(settings: Settings) -> ProjectManagerClient:
    if settings.blockchain_adapter == "web3":
        return ProjectManagerAdapter(settings)
    return MockProjectManagerAdapter()
