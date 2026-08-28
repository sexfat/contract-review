from __future__ import annotations

from typing import Protocol

from app.domain.schemas.retrieval import RetrievalQuery, RetrievedKnowledge


class KnowledgeRepository(Protocol):
    def search(self, query: RetrievalQuery) -> list[RetrievedKnowledge]: ...
