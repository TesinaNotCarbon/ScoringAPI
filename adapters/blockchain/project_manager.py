from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from core.config import Settings
from core.exceptions import BlockchainAdapterError
from models.schemas import ProjectScoringRecord


class ProjectManagerClient(Protocol):
    async def startup(self) -> None:
        ...

    async def shutdown(self) -> None:
        ...

    async def get_project_cell_id(self, project_address: str) -> str:
        ...

    async def get_project_scoring_history(self, project_address: str) -> list[ProjectScoringRecord]:
        ...


class ProjectManagerAdapter:
    """Async web3.py adapter for the ProjectManager smart contract."""

    def __init__(self, settings: Settings) -> None:
        if not settings.rpc_url:
            raise BlockchainAdapterError("RPC_URL is required for ProjectManagerAdapter")
        if not settings.project_manager_address:
            raise BlockchainAdapterError("PROJECT_MANAGER_ADDRESS is required for ProjectManagerAdapter")
        if not settings.project_manager_abi_path:
            raise BlockchainAdapterError("PROJECT_MANAGER_ABI_PATH is required for ProjectManagerAdapter")

        try:
            from web3 import AsyncHTTPProvider, AsyncWeb3
        except ImportError:  # pragma: no cover - import path differs across web3 versions
            try:
                from web3 import AsyncWeb3
                from web3.providers.async_rpc import AsyncHTTPProvider
            except ImportError as exc:
                raise BlockchainAdapterError("web3 is required for ProjectManagerAdapter") from exc

        self.settings = settings
        self._web3_type = AsyncWeb3
        self._w3 = AsyncWeb3(AsyncHTTPProvider(settings.rpc_url))
        self._contract = self._w3.eth.contract(
            address=AsyncWeb3.to_checksum_address(settings.project_manager_address),
            abi=self._load_abi(settings.project_manager_abi_path),
        )

    async def startup(self) -> None:
        return None

    async def shutdown(self) -> None:
        provider = getattr(self._w3, "provider", None)
        disconnect = getattr(provider, "disconnect", None)
        if disconnect:
            await disconnect()

    async def get_project_cell_id(self, project_address: str) -> str:
        address = self._checksum(project_address)
        try:
            return await self._contract.functions.getProjectCellId(address).call()
        except Exception as exc:  # pragma: no cover - web3 exception taxonomy varies
            raise BlockchainAdapterError(f"Could not fetch project cell id: {exc}") from exc

    async def get_project_scoring_history(self, project_address: str) -> list[ProjectScoringRecord]:
        address = self._checksum(project_address)
        try:
            raw_history = await self._contract.functions.getProjectScoringHistory(address).call()
            return [self._parse_history_item(item) for item in raw_history]
        except Exception as exc:  # pragma: no cover - web3 exception taxonomy varies
            raise BlockchainAdapterError(f"Could not fetch project scoring history: {exc}") from exc

    def _checksum(self, address: str) -> str:
        try:
            return self._web3_type.to_checksum_address(address)
        except ValueError as exc:
            raise BlockchainAdapterError(f"Invalid project address: {address}") from exc

    def _load_abi(self, abi_path: str) -> list[dict]:
        path = Path(abi_path)
        try:
            with path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except OSError as exc:
            raise BlockchainAdapterError(f"Could not read ProjectManager ABI: {exc}") from exc
        abi = data.get("abi") if isinstance(data, dict) else data
        if not isinstance(abi, list):
            raise BlockchainAdapterError("ProjectManager ABI file must contain an ABI array")
        return abi

    def _parse_history_item(self, item: object) -> ProjectScoringRecord:
        if isinstance(item, dict):
            return ProjectScoringRecord(
                measurement_date=int(item["measurementDate"]),
                scoring=int(item["scoring"]),
                fraud_scoring=int(item["fraudScoring"]),
                stored_at=int(item["storedAt"]),
            )
        measurement_date, scoring, fraud_scoring, stored_at = item  # type: ignore[misc]
        return ProjectScoringRecord(
            measurement_date=int(measurement_date),
            scoring=int(scoring),
            fraud_scoring=int(fraud_scoring),
            stored_at=int(stored_at),
        )
