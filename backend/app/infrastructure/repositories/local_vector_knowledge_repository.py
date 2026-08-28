from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from app.application.ports.embedding_provider import EmbeddingProvider
from app.domain.errors import KnowledgeIndexUnavailableError, LLMProviderUnavailableError
from app.domain.schemas.legal_source import LegalSource
from app.domain.schemas.retrieval import RetrievalQuery, RetrievedKnowledge
from app.domain.services.knowledge_ranking import rank_by_similarity, resolve_retrieved_knowledge


class LocalVectorKnowledgeRepository:
    """Loads data/legal_sources.seed.json + data/legal_sources.embeddings.npz
    once at construction (mirrors JsonRiskRuleRepository's pattern) and
    ranks candidates in-process with numpy cosine similarity — no
    Postgres/pgvector/Docker (specs/005-rag-and-judge-gate/spec.md
    已確認決策 1)."""

    def __init__(self, seed_path: Path, embeddings_path: Path, embedding_provider: EmbeddingProvider) -> None:
        raw = json.loads(seed_path.read_text(encoding="utf-8"))
        self._sources: dict[str, LegalSource] = {
            entry["knowledge_id"]: LegalSource.model_validate(entry) for entry in raw
        }
        npz = np.load(embeddings_path)
        missing = set(self._sources) - set(npz.files)
        if missing:
            raise KnowledgeIndexUnavailableError()
        self._vectors = {kid: npz[kid] for kid in npz.files if kid in self._sources}
        self._embedding_provider = embedding_provider

    def search(self, query: RetrievalQuery) -> list[RetrievedKnowledge]:
        candidates = [(source, self._vectors[kid]) for kid, source in self._sources.items()]
        if not candidates:
            return []
        try:
            query_vector = self._embedding_provider.embed([query.query_text])[0]
        except LLMProviderUnavailableError:
            raise  # provider-wide outage: fail the whole document (FR8)
        except Exception:  # noqa: BLE001 — single-query failure, not provider-wide
            return []  # treated as "no external sources" (FR9)
        ranked = rank_by_similarity(query_vector, candidates, query)
        return [resolve_retrieved_knowledge(source, self._sources) for source in ranked]


class NullKnowledgeRepository:
    """Safe default while data/legal_sources.embeddings.npz hasn't been
    built yet, or no embedding model is configured — always returns no
    results, so 003's review flow is unaffected until RAG is actually wired
    up (spec.md Failure handling clarification on KNOWLEDGE_INDEX_UNAVAILABLE)."""

    def search(self, query: RetrievalQuery) -> list[RetrievedKnowledge]:
        return []
