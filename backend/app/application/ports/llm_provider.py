from __future__ import annotations

from typing import Protocol

from app.domain.schemas.llm_classification import LLMClassificationRequest, LLMClassificationResult


class LLMProvider(Protocol):
    model_id: str

    def classify_clause(self, request: LLMClassificationRequest) -> LLMClassificationResult:
        """Raises LLMOutputInvalidError (retryable) or
        LLMProviderUnavailableError (fails the whole document)."""
        ...
