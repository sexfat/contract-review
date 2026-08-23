from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ClauseLocation(BaseModel):
    article_no: str | None = None
    heading: str | None = None
    source_start_index: int = Field(ge=0)
    source_end_index: int = Field(ge=0)
    paragraph_ids: list[str] = Field(default_factory=list)
    table_refs: list[str] = Field(default_factory=list)


class ParsedClause(BaseModel):
    clause_id: str = Field(min_length=1)
    clause_type: Literal["other"] = "other"
    original_text: str = Field(min_length=1)
    location: ClauseLocation


class ClauseListResponse(BaseModel):
    document_id: str = Field(min_length=1)
    status: Literal["parsed"] = "parsed"
    clauses: list[ParsedClause]
