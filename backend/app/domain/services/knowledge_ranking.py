from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from app.domain.schemas.legal_source import LegalSource
from app.domain.schemas.retrieval import RetrievalQuery, RetrievedKnowledge


def rank_by_similarity(
    query_vector: Sequence[float],
    candidates: list[tuple[LegalSource, Sequence[float]]],
    query: RetrievalQuery,
) -> list[LegalSource]:
    """Pure Python/numpy, deterministic, no external calls — see
    specs/005-rag-and-judge-gate/spec.md FR1/FR3. Filters to reviewed
    entries matching jurisdiction, with clause_type either unset (applies
    broadly) or matching the query, then ranks by cosine similarity and
    truncates to top_k."""
    filtered = [
        (source, vector)
        for source, vector in candidates
        if source.status == "reviewed"
        and source.jurisdiction == query.jurisdiction
        and (source.clause_type is None or source.clause_type == query.clause_type)
    ]
    filtered.sort(key=lambda pair: -_cosine_similarity(query_vector, pair[1]))
    return [source for source, _ in filtered[: query.top_k]]


def _cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    a_arr, b_arr = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    denom = float(np.linalg.norm(a_arr) * np.linalg.norm(b_arr))
    return float(np.dot(a_arr, b_arr) / denom) if denom else 0.0


def resolve_retrieved_knowledge(
    source: LegalSource, all_sources: dict[str, LegalSource]
) -> RetrievedKnowledge:
    """Chunking 政策第 4 點／spec.md FR11：命中 child 條目（parent_id 不為
    null）時，內容展開為 parent 完整原文，避免子片段脫離上下文被誤讀；
    knowledge_id 仍記錄實際命中的 child ID，供 source_refs 可追溯引用。"""
    display = all_sources[source.parent_id] if source.parent_id else source
    return RetrievedKnowledge(
        knowledge_id=source.knowledge_id,
        parent_id=source.parent_id,
        title=display.title,
        content=display.content,
        source_url=display.source_url,
        effective_date=display.effective_date,
        version=display.version,
    )
