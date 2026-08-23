import pytest
from pydantic import ValidationError

from app.infrastructure.llm.config import LLMSettings


def test_missing_api_key_fails_fast(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
    with pytest.raises(ValidationError):
        LLMSettings(_env_file=None)


def test_defaults_applied_when_api_key_present(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OLLAMA_API_KEY", "test-key")
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)

    settings = LLMSettings(_env_file=None)

    assert settings.ollama_api_key == "test-key"
    assert str(settings.ollama_base_url) == "https://ollama.com/"
    assert settings.ollama_model == "gemma4:31b-cloud"


def test_invalid_base_url_fails_fast(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OLLAMA_API_KEY", "test-key")
    monkeypatch.setenv("OLLAMA_BASE_URL", "not-a-url")
    with pytest.raises(ValidationError):
        LLMSettings(_env_file=None)


def test_non_positive_timeout_fails_fast(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OLLAMA_API_KEY", "test-key")
    with pytest.raises(ValidationError):
        LLMSettings(_env_file=None, request_timeout_seconds=0)
