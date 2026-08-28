from __future__ import annotations

from app.domain.schemas.retrieval import RetrievalQuery, RetrievedKnowledge


class FakeKnowledgeRepository:
    """Test double for KnowledgeRepository: returns a fixed list of
    RetrievedKnowledge regardless of query, and records calls for assertions
    (e.g. "retrieval was not called for a clause with no matched rule")."""

    def __init__(self, results: list[RetrievedKnowledge] | None = None) -> None:
        self._results = results or []
        self.calls: list[RetrievalQuery] = []

    def search(self, query: RetrievalQuery) -> list[RetrievedKnowledge]:
        self.calls.append(query)
        return list(self._results)
