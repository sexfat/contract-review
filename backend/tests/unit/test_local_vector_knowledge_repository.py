import json
from pathlib import Path

import numpy as np
import pytest

from app.domain.errors import KnowledgeIndexUnavailableError, LLMProviderUnavailableError
from app.domain.schemas.clause_type import ClauseType
from app.domain.schemas.retrieval import RetrievalQuery
from app.infrastructure.repositories.local_vector_knowledge_repository import LocalVectorKnowledgeRepository

_ENTRY = {
    "knowledge_id": "civil-492",
    "corpus": "legal_sources",
    "parent_id": None,
    "title": "民法第492條",
    "source_title": "中華民國民法",
    "content": "承攬人完成工作，應使其具備約定之品質...",
    "clause_type": "acceptance",
    "jurisdiction": "TW",
    "source_url": None,
    "effective_date": None,
    "version": 1,
    "status": "reviewed",
    "reviewed_by": "tester",
    "updated_at": "2026-08-28",
}


class _FakeEmbeddingProvider:
    def __init__(self, vector: list[float] | None = None, exception: Exception | None = None) -> None:
        self._vector = vector or [1.0, 0.0]
        self._exception = exception

    def embed(self, texts: list[str]) -> list[list[float]]:
        if self._exception is not None:
            raise self._exception
        return [self._vector for _ in texts]


def _write_seed(tmp_path, entries: list[dict]) -> Path:
    path = tmp_path / "legal_sources.seed.json"
    path.write_text(json.dumps(entries, ensure_ascii=False), encoding="utf-8")
    return path


def _write_embeddings(tmp_path, vectors: dict[str, list[float]]) -> Path:
    path = tmp_path / "legal_sources.embeddings.npz"
    np.savez(path, **{kid: np.asarray(vec, dtype=np.float32) for kid, vec in vectors.items()})
    return path


def test_init_fails_fast_when_knowledge_id_missing_from_embeddings(tmp_path):
    seed_path = _write_seed(tmp_path, [_ENTRY])
    embeddings_path = _write_embeddings(tmp_path, {})  # missing civil-492

    with pytest.raises(KnowledgeIndexUnavailableError):
        LocalVectorKnowledgeRepository(seed_path, embeddings_path, _FakeEmbeddingProvider())


def test_search_returns_matching_entry(tmp_path):
    seed_path = _write_seed(tmp_path, [_ENTRY])
    embeddings_path = _write_embeddings(tmp_path, {"civil-492": [1.0, 0.0]})
    repo = LocalVectorKnowledgeRepository(seed_path, embeddings_path, _FakeEmbeddingProvider([1.0, 0.0]))

    results = repo.search(RetrievalQuery(clause_type=ClauseType.ACCEPTANCE, query_text="驗收條款"))

    assert [r.knowledge_id for r in results] == ["civil-492"]


def test_single_query_embedding_failure_returns_empty_not_raise(tmp_path):
    seed_path = _write_seed(tmp_path, [_ENTRY])
    embeddings_path = _write_embeddings(tmp_path, {"civil-492": [1.0, 0.0]})
    repo = LocalVectorKnowledgeRepository(
        seed_path, embeddings_path, _FakeEmbeddingProvider(exception=ValueError("boom"))
    )

    results = repo.search(RetrievalQuery(clause_type=ClauseType.ACCEPTANCE, query_text="驗收條款"))

    assert results == []


def test_provider_unavailable_error_propagates(tmp_path):
    seed_path = _write_seed(tmp_path, [_ENTRY])
    embeddings_path = _write_embeddings(tmp_path, {"civil-492": [1.0, 0.0]})
    repo = LocalVectorKnowledgeRepository(
        seed_path, embeddings_path, _FakeEmbeddingProvider(exception=LLMProviderUnavailableError())
    )

    with pytest.raises(LLMProviderUnavailableError):
        repo.search(RetrievalQuery(clause_type=ClauseType.ACCEPTANCE, query_text="驗收條款"))
