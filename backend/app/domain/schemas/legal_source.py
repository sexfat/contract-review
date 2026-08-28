from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from app.domain.schemas.clause_type import ClauseType


class LegalSource(BaseModel):
    """Mirrors data/legal_sources.seed.json's schema
    (specs/005-rag-and-judge-gate/contracts/legal_source.schema.json).
    Internal to KnowledgeRepository — never returned to callers directly;
    callers only ever see RetrievedKnowledge (see knowledge_ranking.py)."""

    knowledge_id: str = Field(min_length=1)
    corpus: Literal["legal_sources"]
    parent_id: str | None
    title: str = Field(min_length=1)
    source_title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    clause_type: ClauseType | None
    jurisdiction: str
    source_url: str | None
    effective_date: date | None
    version: int
    status: Literal["draft", "reviewed"]
    reviewed_by: str | None
    updated_at: date
