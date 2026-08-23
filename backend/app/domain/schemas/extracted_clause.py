from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.domain.schemas.clause import ClauseLocation
from app.domain.schemas.clause_type import ClauseType


class ExtractedClause(BaseModel):
    """DEVELOPMENT_SPEC.md §7 ExtractedClause, extended with provenance and a
    human-review flag (see specs/002-llm-clause-classification/design.md)."""

    clause_id: str = Field(min_length=1)
    clause_type: ClauseType
    original_text: str = Field(min_length=1)
    location: ClauseLocation
    plain_summary: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    requires_human_review: bool = False
    model_id: str | None = None


class ClassifiedClauseListResponse(BaseModel):
    document_id: str = Field(min_length=1)
    status: Literal["classified"] = "classified"
    clauses: list[ExtractedClause]
