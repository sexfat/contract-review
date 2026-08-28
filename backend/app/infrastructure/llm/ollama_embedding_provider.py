from __future__ import annotations

import logging

from langchain_ollama import OllamaEmbeddings

from app.infrastructure.llm.config import LLMSettings
from app.infrastructure.llm.exception_mapping import raise_mapped_llm_exception

logger = logging.getLogger("contract_review.llm")


class OllamaEmbeddingProvider:
    """Infrastructure adapter for EmbeddingProvider. Model name is
    unconfirmed (specs/005-rag-and-judge-gate/spec.md 待人工完成事項) —
    callers should not construct this until settings.ollama_embedding_model
    is set; see app/api/dependencies.py get_embedding_provider()."""

    def __init__(self, settings: LLMSettings) -> None:
        assert settings.ollama_embedding_model is not None
        self._client = OllamaEmbeddings(
            model=settings.ollama_embedding_model,
            base_url=str(settings.ollama_embedding_base_url),
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            return self._client.embed_documents(texts)
        except Exception as exc:  # noqa: BLE001 — classified by raise_mapped_llm_exception
            raise_mapped_llm_exception(exc, logger=logger, log_extra={})
