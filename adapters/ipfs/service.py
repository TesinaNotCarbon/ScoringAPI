from __future__ import annotations

import asyncio
import json
import re
from typing import Any

import aiohttp

from core.config import Settings
from core.exceptions import IPFSDownloadError, InvalidCellIdError
from models.schemas import ProjectGeometry

_CELL_ID_PATTERN = re.compile(r"^[a-zA-Z0-9._:-]{3,128}$")


class IPFSService:
    """Download GeoJSON documents from Pinata/IPFS safely."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._session: aiohttp.ClientSession | None = None
        self._sem = asyncio.Semaphore(settings.max_concurrent_downloads)

    async def startup(self) -> None:
        timeout = aiohttp.ClientTimeout(total=self.settings.ipfs_timeout_seconds)
        headers = {}
        if self.settings.pinata_jwt:
            headers["Authorization"] = f"Bearer {self.settings.pinata_jwt}"
        self._session = aiohttp.ClientSession(timeout=timeout, headers=headers)

    async def shutdown(self) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None

    async def download_geojson(self, cell_id: str) -> ProjectGeometry:
        self._validate_cell_id(cell_id)
        data = await self._download_json(cell_id)
        return ProjectGeometry(cell_id=cell_id, geojson=data)

    async def _download_json(self, cell_id: str) -> dict[str, Any]:
        if self._session is None:
            raise IPFSDownloadError("IPFS HTTP session is not initialized")

        base_url = str(self.settings.pinata_gateway_base_url).rstrip("/")
        url = f"{base_url}/{cell_id}"

        async with self._sem:
            for attempt in range(3):
                async with self._session.get(url) as response:
                    if response.status == 200:
                        return await self._read_bounded_json(response, cell_id)

                    if response.status == 429 and attempt < 2:
                        retry_after = response.headers.get("Retry-After")
                        sleep_seconds = float(retry_after) if retry_after and retry_after.isdigit() else 1.0
                        await asyncio.sleep(max(0.5, sleep_seconds))
                        continue

                    text = await response.text()
                    raise IPFSDownloadError(
                        f"Failed to fetch CID {cell_id}. Status {response.status}. Body: {text[:300]}"
                    )

        raise IPFSDownloadError(f"Exceeded retries for CID {cell_id}")  # pragma: no cover - defensive guard

    async def _read_bounded_json(self, response: aiohttp.ClientResponse, cell_id: str) -> dict[str, Any]:
        content_type = response.headers.get("Content-Type", "")
        if content_type and "json" not in content_type and "octet-stream" not in content_type:
            raise IPFSDownloadError(f"CID {cell_id} returned unsupported content-type")

        body = await response.content.read(self.settings.ipfs_max_bytes + 1)
        if len(body) > self.settings.ipfs_max_bytes:
            raise IPFSDownloadError(f"CID {cell_id} exceeds max allowed size")

        try:
            parsed = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise IPFSDownloadError(f"CID {cell_id} returned invalid JSON") from exc

        if not isinstance(parsed, dict):
            raise IPFSDownloadError(f"CID {cell_id} JSON root must be an object")
        return parsed

    def _validate_cell_id(self, cell_id: str) -> None:
        if not _CELL_ID_PATTERN.fullmatch(cell_id):
            raise InvalidCellIdError("Invalid cell_id format")
