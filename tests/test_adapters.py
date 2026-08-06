from __future__ import annotations

import asyncio
import json
import sys
import types
from pathlib import Path
from typing import Any

import aiohttp
import pytest

from adapters.ai.groq_provider import GroqAIProvider
from adapters.blockchain.project_manager import ProjectManagerAdapter
from adapters.ipfs.service import IPFSService
from adapters.satellite.provider import HTTPSatelliteImageryProvider, MockSatelliteImageryProvider
from core.config import Settings
from core.exceptions import AIProviderError, BlockchainAdapterError, IPFSDownloadError, InvalidCellIdError, SatelliteDataError
from models.schemas import Indicators, ProjectGeometry, ProjectScoringAnalysisRequest


class FakeContent:
    def __init__(self, body: bytes) -> None:
        self.body = body

    async def read(self, _: int) -> bytes:
        return self.body


class FakeResponse:
    def __init__(self, status: int = 200, body: bytes = b"{}", headers: dict[str, str] | None = None) -> None:
        self.status = status
        self.headers = headers or {"Content-Type": "application/json"}
        self.content = FakeContent(body)

    async def __aenter__(self) -> "FakeResponse":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def text(self) -> str:
        return self.content.body.decode("utf-8", errors="replace")

    async def json(self) -> Any:
        return json.loads(await self.text())


class FakeGetSession:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.closed = False
        self.urls: list[str] = []

    def get(self, url: str) -> FakeResponse:
        self.urls.append(url)
        return self.responses.pop(0)

    async def close(self) -> None:
        self.closed = True


class FakePostSession:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.closed = False
        self.posts: list[tuple[str, dict[str, Any]]] = []

    def post(self, url: str, json: dict[str, Any]) -> FakeResponse:
        self.posts.append((url, json))
        return self.response

    async def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_ipfs_download_geojson_success_startup_and_shutdown(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_client_session(**kwargs: Any) -> FakeGetSession:
        captured.update(kwargs)
        return FakeGetSession([FakeResponse(body=b'{"type":"Polygon"}')])

    monkeypatch.setattr(aiohttp, "ClientSession", fake_client_session)
    service = IPFSService(Settings(environment="test", pinata_gateway_base_url="https://example.test/ipfs", pinata_jwt="jwt"))
    await service.startup()

    geometry = await service.download_geojson("valid-cell")
    session = service._session
    await service.shutdown()

    assert geometry == ProjectGeometry(cell_id="valid-cell", geojson={"type": "Polygon"})
    assert session.urls == ["https://example.test/ipfs/valid-cell"]  # type: ignore[union-attr]
    assert session.closed is True  # type: ignore[union-attr]
    assert captured["headers"] == {"Authorization": "Bearer jwt"}
    assert service._session is None


@pytest.mark.asyncio
async def test_ipfs_retries_429_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    service = IPFSService(Settings(environment="test"))
    service._session = FakeGetSession([
        FakeResponse(status=429, body=b"rate", headers={"Retry-After": "0"}),
        FakeResponse(body=b'{"ok":true}'),
    ])  # type: ignore[assignment]
    slept: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        slept.append(seconds)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    assert await service._download_json("valid-cell") == {"ok": True}
    assert slept == [0.5]


@pytest.mark.asyncio
async def test_ipfs_errors() -> None:
    service = IPFSService(Settings(environment="test", ipfs_max_bytes=2))

    with pytest.raises(InvalidCellIdError):
        await service.download_geojson("no")
    with pytest.raises(IPFSDownloadError, match="not initialized"):
        await service._download_json("valid-cell")

    assert service._validate_cell_id("abc") is None
    assert await service._read_bounded_json(FakeResponse(body=b"{}"), "cid") == {}

    with pytest.raises(IPFSDownloadError, match="unsupported content-type"):
        await service._read_bounded_json(FakeResponse(headers={"Content-Type": "text/html"}), "cid")
    with pytest.raises(IPFSDownloadError, match="exceeds"):
        await service._read_bounded_json(FakeResponse(body=b"{} "), "cid")
    with pytest.raises(IPFSDownloadError, match="invalid JSON"):
        await service._read_bounded_json(FakeResponse(body=b"{"), "cid")
    with pytest.raises(IPFSDownloadError, match="root must be an object"):
        await service._read_bounded_json(FakeResponse(body=b"[]"), "cid")

    service._session = FakeGetSession([FakeResponse(status=500, body=b"boom")])  # type: ignore[assignment]
    with pytest.raises(IPFSDownloadError, match="Status 500"):
        await service._download_json("valid-cell")


@pytest.mark.asyncio
async def test_groq_provider_startup_success_extracts_content_and_direct_json(monkeypatch: pytest.MonkeyPatch) -> None:
    request = ProjectScoringAnalysisRequest(
        project_id="0x0000000000000000000000000000000000000001",
        cell_id="cell",
        measurement_date=1,
        indicators=Indicators(ndvi=0.1, savi=0.2, evi=0.3, nbr=0.4),
        cloud_coverage=0.1,
    )
    body = json.dumps({"choices": [{"message": {"content": '{"scoring":"0.70","fraud_scoring":"0.20"}'}}]}).encode()
    session = FakePostSession(FakeResponse(body=body))
    monkeypatch.setattr(aiohttp, "ClientSession", lambda **kwargs: session)
    provider = GroqAIProvider(Settings(environment="test", groq_api_key="key"))

    result = await provider.analyze_project_scoring(request)
    await provider.shutdown()

    assert result.scoring == "0.70"
    assert result.fraud_scoring == "0.20"
    assert session.posts[0][0].endswith("/chat/completions")
    assert "Project data" in provider._build_prompt(request)
    assert provider._extract_content({"scoring": "0.10", "fraud_scoring": "0.90"}) == '{"scoring": "0.10", "fraud_scoring": "0.90"}'
    assert session.closed is True


@pytest.mark.asyncio
async def test_groq_provider_errors() -> None:
    with pytest.raises(AIProviderError, match="GROQ_API_KEY"):
        GroqAIProvider(Settings(environment="test", groq_api_key=None))

    provider = GroqAIProvider(Settings(environment="test", groq_api_key="key"))
    with pytest.raises(AIProviderError, match="does not contain"):
        provider._extract_content({"choices": []})

    request = ProjectScoringAnalysisRequest(
        project_id="0x0000000000000000000000000000000000000001",
        cell_id="cell",
        measurement_date=1,
        indicators=Indicators(ndvi=0.1, savi=0.2, evi=0.3, nbr=0.4),
        cloud_coverage=0.1,
    )
    provider._session = FakePostSession(FakeResponse(status=400, body=b"bad"))  # type: ignore[assignment]
    with pytest.raises(AIProviderError, match="Groq returned 400"):
        await provider.analyze_project_scoring(request)

    provider._session = FakePostSession(FakeResponse(body=b"not-json"))  # type: ignore[assignment]
    with pytest.raises(AIProviderError, match="could not be processed"):
        await provider.analyze_project_scoring(request)


@pytest.mark.asyncio
async def test_http_satellite_provider_startup_success_and_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(environment="test", satellite_provider_base_url="https://sat.test", satellite_provider_api_key="token")
    body = b'{"nir":0.5,"red":0.2,"blue":0.1,"swir":0.3,"timestamp":"2026-01-01T00:00:00Z","cloud_coverage":0.1}'
    session = FakePostSession(FakeResponse(body=body))
    monkeypatch.setattr(aiohttp, "ClientSession", lambda **kwargs: session)
    provider = HTTPSatelliteImageryProvider(settings)

    observation = await provider.get_observation(ProjectGeometry(cell_id="cell", geojson={"type": "Point"}), "2026-01-01")
    await provider.shutdown()

    assert observation.nir == 0.5
    assert session.posts[0][0] == "https://sat.test/observations"
    assert provider._session is None

    with pytest.raises(SatelliteDataError, match="base_url"):
        HTTPSatelliteImageryProvider(Settings(environment="test", satellite_provider_base_url=None))

    provider = HTTPSatelliteImageryProvider(settings)
    provider._session = FakePostSession(FakeResponse(status=500, body=b'{"error":"bad"}'))  # type: ignore[assignment]
    with pytest.raises(SatelliteDataError, match="returned 500"):
        await provider.get_observation(ProjectGeometry(cell_id="cell", geojson={}))

    provider._session = FakePostSession(FakeResponse(body=b'{"nir":"bad"}'))  # type: ignore[assignment]
    with pytest.raises(SatelliteDataError, match="could not be processed"):
        await provider.get_observation(ProjectGeometry(cell_id="cell", geojson={}))


def test_mock_satellite_edge_helpers(tmp_path: Path) -> None:
    profiles = tmp_path / "profiles.json"
    profiles.write_text(json.dumps({"profiles": {"a": {"nir": 2, "red": -1, "blue": 0, "swir": 0, "cloud_coverage": 0}}}), encoding="utf-8")
    provider = MockSatelliteImageryProvider(profiles)
    provider._load_profiles()

    assert provider._profile_for_cell_id("unknown").nir == 2
    assert provider._date_adjustment("bad-date").nir == 0
    assert provider._date_adjustment("2026-04-01").nir == 0
    assert provider._geometry_adjustment({}) == 0.0
    assert provider._extract_points({"type": "Feature", "geometry": None}) == []
    assert provider._extract_points({"type": "FeatureCollection", "features": [{"type": "Point", "coordinates": [1, 2]}, "bad"]}) == [(1.0, 2.0)]
    assert provider._walk_coordinates("bad") == []
    assert provider._clamp(2) == 1.0
    assert provider._clamp(-1) == 0.0

    empty = tmp_path / "empty.json"
    empty.write_text(json.dumps({"profiles": {}}), encoding="utf-8")
    with pytest.raises(ValueError, match="at least one profile"):
        MockSatelliteImageryProvider(empty)._load_profiles()


@pytest.mark.asyncio
async def test_project_manager_helpers_and_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(BlockchainAdapterError, match="RPC_URL"):
        ProjectManagerAdapter(Settings(environment="test"))
    with pytest.raises(BlockchainAdapterError, match="PROJECT_MANAGER_ADDRESS"):
        ProjectManagerAdapter(Settings(environment="test", rpc_url="http://rpc"))
    with pytest.raises(BlockchainAdapterError, match="PROJECT_MANAGER_ABI_PATH"):
        ProjectManagerAdapter(Settings(environment="test", rpc_url="http://rpc", project_manager_address="0x0000000000000000000000000000000000000001"))

    abi_file = tmp_path / "abi.json"
    abi_file.write_text(json.dumps({"abi": []}), encoding="utf-8")

    class FakeProvider:
        def __init__(self, url: str) -> None:
            self.url = url
            self.disconnected = False

        async def disconnect(self) -> None:
            self.disconnected = True

    class FakeFunction:
        def __init__(self, result: Any = None, error: Exception | None = None) -> None:
            self.result = result
            self.error = error

        async def call(self) -> Any:
            if self.error:
                raise self.error
            return self.result

    class FakeFunctions:
        def __init__(self) -> None:
            self.cell_error: Exception | None = None
            self.history_error: Exception | None = None

        def getProjectCellId(self, address: str) -> FakeFunction:
            return FakeFunction("cell-1", self.cell_error)

        def getProjectScoringHistory(self, address: str) -> FakeFunction:
            return FakeFunction([(1, 2, 3, 4), {"measurementDate": 5, "scoring": 6, "fraudScoring": 7, "storedAt": 8}], self.history_error)

    class FakeContract:
        def __init__(self) -> None:
            self.functions = FakeFunctions()

    contract = FakeContract()

    class FakeEth:
        def contract(self, **kwargs: Any) -> FakeContract:
            return contract

    class FakeWeb3:
        def __init__(self, provider: FakeProvider) -> None:
            self.provider = provider
            self.eth = FakeEth()

        @staticmethod
        def to_checksum_address(address: str) -> str:
            if address == "bad":
                raise ValueError("bad")
            return address.upper()

    fake_web3_module = types.SimpleNamespace(AsyncHTTPProvider=FakeProvider, AsyncWeb3=FakeWeb3)
    monkeypatch.setitem(sys.modules, "web3", fake_web3_module)

    adapter = ProjectManagerAdapter(Settings(
        environment="test",
        rpc_url="http://rpc",
        project_manager_address="0x0000000000000000000000000000000000000001",
        project_manager_abi_path=str(abi_file),
    ))

    assert await adapter.get_project_cell_id("0x0000000000000000000000000000000000000001") == "cell-1"
    history = await adapter.get_project_scoring_history("0x0000000000000000000000000000000000000001")
    assert [item.scoring for item in history] == [2, 6]
    assert adapter._checksum("0xabc") == "0XABC"
    with pytest.raises(BlockchainAdapterError, match="Invalid project address"):
        adapter._checksum("bad")

    contract.functions.cell_error = RuntimeError("boom")
    with pytest.raises(BlockchainAdapterError, match="Could not fetch project cell id"):
        await adapter.get_project_cell_id("0x0000000000000000000000000000000000000001")
    contract.functions.history_error = RuntimeError("boom")
    with pytest.raises(BlockchainAdapterError, match="Could not fetch project scoring history"):
        await adapter.get_project_scoring_history("0x0000000000000000000000000000000000000001")

    await adapter.startup()
    await adapter.shutdown()

    missing = tmp_path / "missing.json"
    adapter.__new__(ProjectManagerAdapter)
    with pytest.raises(BlockchainAdapterError, match="Could not read"):
        ProjectManagerAdapter._load_abi(adapter, str(missing))

    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"abi": {}}), encoding="utf-8")
    with pytest.raises(BlockchainAdapterError, match="must contain"):
        ProjectManagerAdapter._load_abi(adapter, str(bad))
