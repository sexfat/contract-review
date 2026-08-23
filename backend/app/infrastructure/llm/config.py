from __future__ import annotations

from dotenv import load_dotenv
from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseSettings):
    """Loaded from environment / .env — never hardcode credentials or model
    choice in application code (DEVELOPMENT_SPEC.md §4, §12)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ollama_api_key: str = Field(min_length=1, validation_alias="OLLAMA_API_KEY")
    ollama_base_url: AnyHttpUrl = Field(default=AnyHttpUrl("https://ollama.com"), validation_alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(min_length=1, default="gemma4:31b-cloud", validation_alias="OLLAMA_MODEL")
    request_timeout_seconds: float = Field(default=30.0, gt=0)


def load_llm_settings() -> LLMSettings:
    """`load_dotenv()` populates os.environ (not just this settings object) so
    the underlying `ollama` client — which reads OLLAMA_API_KEY from the
    process environment itself — picks up the same credential.

    Fails fast on the *first call to `POST /classify`* (this is a lazily
    resolved FastAPI dependency, not a startup hook) rather than the whole
    process failing to boot — that keeps 001's upload/parse/health endpoints
    usable in environments without an LLM key configured (e.g. local dev,
    CI). See specs/002-llm-clause-classification/design.md."""
    load_dotenv()
    return LLMSettings()
