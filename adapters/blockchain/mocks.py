from __future__ import annotations

from models.schemas import ProjectScoringRecord


class MockProjectManagerAdapter:
    """Deterministic local ProjectManager replacement for development/tests."""

    _DEFAULT_PROJECT = "0x0000000000000000000000000000000000000001"

    def __init__(self) -> None:
        self._cell_ids = {
            self._DEFAULT_PROJECT: "test-cell-123",
            "0x0000000000000000000000000000000000000002": "healthy-forest-cell",
        }
        self._history = {
            self._DEFAULT_PROJECT: [
                ProjectScoringRecord(measurement_date=1782172800, scoring=72, fraud_scoring=12, stored_at=1782176400),
                ProjectScoringRecord(measurement_date=1784764800, scoring=76, fraud_scoring=10, stored_at=1784768400),
            ]
        }

    async def startup(self) -> None:
        return None

    async def shutdown(self) -> None:
        return None

    async def get_project_cell_id(self, project_address: str) -> str:
        return self._cell_ids.get(project_address.lower(), self._fallback_cell_id(project_address))

    async def get_project_scoring_history(self, project_address: str) -> list[ProjectScoringRecord]:
        return list(self._history.get(project_address.lower(), []))

    def _fallback_cell_id(self, project_address: str) -> str:
        return f"project-{project_address[-8:].lower()}"
