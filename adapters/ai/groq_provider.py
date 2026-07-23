from __future__ import annotations

import json
from typing import Any, Protocol

import aiohttp
from pydantic import BaseModel, Field, ValidationError

from core.config import Settings
from core.exceptions import AIProviderError
from models.schemas import AIScoringResponse, ProjectScoringAnalysisRequest


class AIProvider(Protocol):
    """Boundary for LLM/AI project scoring providers."""

    async def startup(self) -> None:
        ...

    async def shutdown(self) -> None:
        ...

    async def analyze_project_scoring(self, request: ProjectScoringAnalysisRequest) -> AIScoringResponse:
        ...


class GroqMessage(BaseModel):
    role: str
    content: str


class GroqChatCompletionRequest(BaseModel):
    model: str
    messages: list[GroqMessage]
    temperature: float = 0.0
    response_format: dict[str, str] = Field(default_factory=lambda: {"type": "json_object"})


class GroqAIProvider:
    """Groq OpenAI-compatible chat adapter."""

    def __init__(self, settings: Settings) -> None:
        if not settings.groq_api_key:
            raise AIProviderError("GROQ_API_KEY is required to use GroqAIProvider")
        self.settings = settings
        self._session: aiohttp.ClientSession | None = None

    async def startup(self) -> None:
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.settings.groq_timeout_seconds),
            headers={
                "Authorization": f"Bearer {self.settings.groq_api_key}",
                "Content-Type": "application/json",
            },
        )

    async def shutdown(self) -> None:
        if self._session:
            await self._session.close()
            self._session = None

    async def analyze_project_scoring(self, request: ProjectScoringAnalysisRequest) -> AIScoringResponse:
        if self._session is None:
            await self.startup()

        payload = GroqChatCompletionRequest(
            model=self.settings.groq_model,
            messages=[
                GroqMessage(
                    role="system",
                    content=(
                        "You are a scoring engine for carbon/reforestation projects. "
                        "Return only valid JSON with exactly these two keys: scoring and fraud_scoring. "
                        "Both values must be strings containing a number between 0.00 and 1.00 with exactly two decimals. "
                        "scoring is the environmental/carbon integrity score, where 0.00 is extremely poor evidence and 1.00 is excellent evidence. "
                        "fraud_scoring is fraud risk, where 0.00 means no fraud risk and 1.00 means maximum fraud risk. "
                        "Do not include explanations, markdown, or extra keys."
                    ),
                ),
                GroqMessage(role="user", content=self._build_prompt(request)),
            ],
        ).model_dump()

        try:
            assert self._session is not None
            url = f"{str(self.settings.groq_base_url).rstrip('/')}{self.settings.groq_chat_path}"
            async with self._session.post(url, json=payload) as response:
                text = await response.text()
                if response.status >= 400:
                    raise AIProviderError(f"Groq returned {response.status}: {text[:300]}")
                data = json.loads(text)
                content = self._extract_content(data)
                return AIScoringResponse.model_validate_json(content)
        except (aiohttp.ClientError, json.JSONDecodeError, ValidationError) as exc:
            raise AIProviderError(f"Groq response could not be processed: {exc}") from exc

    def _build_prompt(self, request: ProjectScoringAnalysisRequest) -> str:
        return (
            "Evaluate this carbon/reforestation project using current satellite indicators and previous on-chain scoring history.\n"
            "Use current indicators to determine scoring. Use previous scoring history, score volatility, suspicious jumps, "
            "repeated fraud scores, indicator inconsistency, burn/logging signals, and cloud coverage to determine fraud_scoring.\n"
            "Consider NDVI, SAVI, EVI, NBR, cloud coverage, sudden large improvements or regressions, repeated high fraud scores, "
            "and whether the current state is inconsistent with historical trend.\n"
            "Return only JSON in this exact shape: {\"scoring\": \"0.00\", \"fraud_scoring\": \"0.00\"}\n"
            f"Project data: {request.model_dump_json()}"
        )

    def _extract_content(self, data: dict[str, Any]) -> str:
        choices = data.get("choices") or []
        if choices:
            message = choices[0].get("message") or {}
            if isinstance(message.get("content"), str):
                return message["content"]
        if isinstance(data.get("scoring"), str) and isinstance(data.get("fraud_scoring"), str):
            return json.dumps(data)
        raise AIProviderError("Groq response does not contain scoring content")
