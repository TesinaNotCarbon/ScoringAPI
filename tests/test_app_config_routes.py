from __future__ import annotations

import importlib
import runpy

from fastapi.testclient import TestClient
import pytest

import core.app as core_app
from core.app import create_app
from core.config import Settings, get_settings
from core.exceptions import AIProviderError, BlockchainAdapterError, InvalidCellIdError, IPFSDownloadError, SatelliteDataError, ScoringAPIError


class RaisingScoringService:
    def __init__(self, exc: Exception) -> None:
        self.exc = exc

    async def score_project(self, project_id: str):  # type: ignore[no-untyped-def]
        raise self.exc

    async def score_project_for_consensus(self, project_id: str):  # type: ignore[no-untyped-def]
        raise self.exc


@pytest.mark.parametrize("exc", [InvalidCellIdError("bad cell"), BlockchainAdapterError("chain bad")])
def test_score_routes_translate_422_errors(exc: Exception) -> None:
    app = create_app(Settings(environment="test"))
    with TestClient(app) as client:
        app.state.scoring_service = RaisingScoringService(exc)
        response = client.get("/score/0x0000000000000000000000000000000000000001")
        chainlink = client.get("/chainlink/score/0x0000000000000000000000000000000000000001")

    assert response.status_code == 422
    assert response.json()["detail"] == str(exc)
    assert chainlink.status_code == 422


@pytest.mark.parametrize("exc", [IPFSDownloadError("ipfs bad"), SatelliteDataError("sat bad"), AIProviderError("ai bad")])
def test_score_routes_translate_502_errors(exc: Exception) -> None:
    app = create_app(Settings(environment="test"))
    with TestClient(app) as client:
        app.state.scoring_service = RaisingScoringService(exc)
        response = client.post("/score", json={"project_id": "0x0000000000000000000000000000000000000001"})
        chainlink = client.get("/chainlink/score/0x0000000000000000000000000000000000000001")

    assert response.status_code == 502
    assert response.json()["detail"] == str(exc)
    assert chainlink.status_code == 502


def test_scoring_api_error_handler() -> None:
    app = create_app(Settings(environment="test"))

    @app.get("/raises-scoring-error")
    async def raises_scoring_error() -> None:
        raise ScoringAPIError("handled")

    with TestClient(app) as client:
        response = client.get("/raises-scoring-error")

    assert response.status_code == 400
    assert response.json() == {"detail": "handled", "code": "ScoringAPIError"}


def test_app_builders_and_cors(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(
        environment="test",
        cors_origins="https://a.test, https://b.test",
        pinata_jwt=None,
        satellite_provider="mock",
        blockchain_adapter="mock",
    )

    assert settings.cors_origins == ["https://a.test", "https://b.test"]
    assert Settings(environment="test", cors_origins=["https://list.test"]).cors_origins == ["https://list.test"]
    assert core_app._build_ipfs_service(settings).__class__.__name__ == "MockIPFSService"
    assert core_app._build_satellite_provider(settings).__class__.__name__ == "MockSatelliteImageryProvider"
    assert core_app._build_project_manager(settings).__class__.__name__ == "MockProjectManagerAdapter"

    with TestClient(create_app(settings)) as client:
        response = client.options(
            "/score/0x0000000000000000000000000000000000000001",
            headers={"Origin": "https://a.test", "Access-Control-Request-Method": "GET"},
        )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://a.test"

    http_settings = Settings(environment="test", satellite_provider="http", satellite_provider_base_url="https://sat.test")
    assert core_app._build_satellite_provider(http_settings).__class__.__name__ == "HTTPSatelliteImageryProvider"
    assert core_app._build_ipfs_service(Settings(environment="production", pinata_jwt="jwt")).__class__.__name__ == "IPFSService"
    reloaded_core_app = importlib.reload(core_app)
    assert reloaded_core_app._build_ai_provider(Settings(environment="test", groq_api_key="key")).__class__.__name__ == "GroqAIProvider"

    with pytest.raises(BlockchainAdapterError):
        core_app._build_project_manager(Settings(environment="test", blockchain_adapter="web3"))


def test_settings_empty_url_and_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    assert Settings(environment="test", satellite_provider_base_url="").satellite_provider_base_url is None

    get_settings.cache_clear()
    monkeypatch.setenv("APP_NAME", "Env API")
    assert get_settings().app_name == "Env API"
    get_settings.cache_clear()


def test_main_module_import_and_run(monkeypatch: pytest.MonkeyPatch) -> None:
    imported = importlib.import_module("main")
    assert imported.app is not None

    calls: list[dict[str, object]] = []

    def fake_run(app: str, **kwargs: object) -> None:
        calls.append({"app": app, **kwargs})

    monkeypatch.setattr("uvicorn.run", fake_run)
    runpy.run_module("main", run_name="__main__")

    assert calls[0]["app"] == "main:app"
    assert "host" in calls[0]
