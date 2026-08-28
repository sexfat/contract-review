from __future__ import annotations

from typing import Protocol


class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Same exception semantics as RiskAssessmentProvider:
        LLMProviderUnavailableError fails the whole document. A single
        query's embedding failure (not a provider-wide outage) is caught by
        the caller (LocalVectorKnowledgeRepository) and treated as "no
        external sources" — see spec.md FR9."""
        ...
