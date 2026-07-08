from __future__ import annotations

import json
from typing import Any, Protocol

import aiohttp
from pydantic import BaseModel, Field, ValidationError

from core.config import Settings
from core.exceptions import AIProviderError
from models.schemas import FraudAnalysis, FraudAnalysisRequest


class AIProvider(Protocol):
    """Boundary for LLM/AI fraud analysis providers."""

    async def startup(self) -> None:
        ...

    async def shutdown(self) -> None:
        ...

    async def analyze_fraud(self, request: FraudAnalysisRequest) -> FraudAnalysis:
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
    """Groq OpenAI-compatible chat adapter.

    Groq exposes an OpenAI-compatible chat completions API at
    https://api.groq.com/openai/v1/chat/completions. The free tier can be used
    by providing a Groq API key through GROQ_API_KEY.
    """

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

    async def analyze_fraud(self, request: FraudAnalysisRequest) -> FraudAnalysis:
        if self._session is None:
            await self.startup()

        payload = GroqChatCompletionRequest(
            model=self.settings.groq_model,
            messages=[
                GroqMessage(
                    role="system",
                    content=(
                        "Eres un auditor de fraude en proyectos de carbono basados en imágenes satelitales. "
                        "Responde exclusivamente JSON válido con las claves criticality y description. "
                        "criticality debe ser low, medium o high. "
                        "description debe incluir un resumen breve y una recomendación para un administrador."
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
                return FraudAnalysis.model_validate_json(content)
        except (aiohttp.ClientError, json.JSONDecodeError, ValidationError) as exc:
            raise AIProviderError(f"Groq response could not be processed: {exc}") from exc

    def _build_prompt(self, request: FraudAnalysisRequest) -> str:
        return (
            "Analiza posible fraude con estos datos del proyecto y mediciones.\n"
            "Devuelve únicamente JSON con este schema:\n"
            "{\"criticality\": \"low|medium|high\", \"description\": \"resumen y recomendación\"}\n"
            "Considera flags, score actual, comparación contra score anterior, tendencia e indicadores satelitales.\n"
            f"Datos: {request.model_dump_json()}"
        )

    def _extract_content(self, data: dict[str, Any]) -> str:
        choices = data.get("choices") or []
        if choices:
            message = choices[0].get("message") or {}
            if isinstance(message.get("content"), str):
                return message["content"]
        if isinstance(data.get("criticality"), str):
            return json.dumps(data)
        raise AIProviderError("Groq response does not contain analyzable content")
