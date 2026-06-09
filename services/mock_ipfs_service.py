from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from models.schemas import ProjectGeometry
from services.ipfs_service import IPFSService

_MOCK_GEOJSONS_PATH = Path(__file__).with_name("mocks") / "mock_geojsons.json"


class MockIPFSService(IPFSService):
    """Local deterministic IPFS replacement for development and tests.

    Known mock cell ids are loaded from ``mock_geojsons.json``. Unknown valid
    cell ids are mapped deterministically to one of the sample geometries so the
    API remains useful for Chainlink/local testing without Pinata credentials.
    """

    def __init__(self, settings) -> None:  # type: ignore[no-untyped-def]
        super().__init__(settings)
        self._geojsons: dict[str, dict[str, Any]] = {}

    async def startup(self) -> None:
        self._geojsons = self._load_geojsons()

    async def shutdown(self) -> None:
        return None

    async def download_geojson(self, cell_id: str) -> ProjectGeometry:
        self._validate_cell_id(cell_id)
        geojson = self._geojsons.get(cell_id) or self._fallback_geojson(cell_id)
        return ProjectGeometry(cell_id=cell_id, geojson=geojson)

    def _load_geojsons(self) -> dict[str, dict[str, Any]]:
        with _MOCK_GEOJSONS_PATH.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data, dict):
            raise ValueError("mock_geojsons.json must contain an object")
        return data

    def _fallback_geojson(self, cell_id: str) -> dict[str, Any]:
        samples = list(self._geojsons.values())
        if not samples:
            raise ValueError("No mock GeoJSON samples are available")
        checksum = sum(ord(char) for char in cell_id)
        return samples[checksum % len(samples)]
