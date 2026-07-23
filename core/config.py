from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Scoring API"
    app_version: str = "1.0.0"
    environment: Literal["local", "test", "staging", "production"] = "local"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 3000

    cors_origins: str | list[str] = Field(default_factory=list)

    pinata_gateway_base_url: AnyHttpUrl = "https://gateway.pinata.cloud/ipfs"
    pinata_jwt: str | None = None
    ipfs_timeout_seconds: float = 10.0
    ipfs_max_bytes: int = 1_000_000
    max_concurrent_downloads: int = 10

    satellite_timeout_seconds: float = 10.0
    satellite_provider: Literal["mock", "http"] = "mock"
    satellite_provider_base_url: AnyHttpUrl | None = None
    satellite_provider_observation_path: str = "/observations"
    satellite_provider_api_key: str | None = None

    rpc_url: str | None = None
    project_manager_address: str | None = None
    project_manager_abi_path: str | None = None
    blockchain_adapter: Literal["mock", "web3"] = "mock"

    groq_base_url: AnyHttpUrl = "https://api.groq.com/openai/v1"
    groq_chat_path: str = "/chat/completions"
    groq_api_key: str | None = None
    groq_model: str = "llama-3.1-8b-instant"
    groq_timeout_seconds: float = 20.0

    approve_threshold: int = Field(default=70, ge=0, le=100)
    review_threshold: int = Field(default=45, ge=0, le=100)
    drastic_improvement_threshold: int = Field(default=25, ge=1, le=100)

    log_level: str = "INFO"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("satellite_provider_base_url", mode="before")
    @classmethod
    def empty_url_as_none(cls, value: str | None) -> str | None:
        if value == "":
            return None
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
