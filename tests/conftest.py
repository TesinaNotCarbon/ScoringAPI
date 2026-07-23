from __future__ import annotations

import pytest

import core.app
from models.schemas import AIScoringResponse, ProjectScoringAnalysisRequest


class TestAIProvider:
    async def startup(self) -> None:
        return None

    async def shutdown(self) -> None:
        return None

    async def analyze_project_scoring(self, request: ProjectScoringAnalysisRequest) -> AIScoringResponse:
        fraud = "0.50" if request.flags else "0.10"
        return AIScoringResponse(scoring="0.80", fraud_scoring=fraud)


@pytest.fixture(autouse=True)
def stub_ai_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(core.app, "_build_ai_provider", lambda settings: TestAIProvider())
