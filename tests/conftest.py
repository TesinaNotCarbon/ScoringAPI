from __future__ import annotations

import pytest

import core.app
from models.schemas import FraudAnalysis, FraudAnalysisRequest


class TestAIProvider:
    async def startup(self) -> None:
        return None

    async def shutdown(self) -> None:
        return None

    async def analyze_fraud(self, request: FraudAnalysisRequest) -> FraudAnalysis:
        flags = set(request.flags)
        if "possible_burn_or_logging" in flags or request.score < 45:
            criticality = "high"
        elif flags or request.score_trend in {"regressed", "suspicious_improvement"}:
            criticality = "medium"
        else:
            criticality = "low"
        return FraudAnalysis(
            criticality=criticality,
            description=f"test analysis; trend={request.score_trend}; flags={','.join(request.flags)}",
        )


@pytest.fixture(autouse=True)
def stub_ai_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(core.app, "_build_ai_provider", lambda settings: TestAIProvider())
