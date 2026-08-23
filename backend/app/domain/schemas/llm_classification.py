from __future__ import annotations

from pydantic import BaseModel, Field

from app.domain.schemas.clause_type import ClauseType


class LLMClassificationRequest(BaseModel):
    clause_id: str = Field(min_length=1)
    original_text: str = Field(min_length=1)


class LLMClassificationResult(BaseModel):
    clause_id: str = Field(min_length=1)
    clause_type: ClauseType
    plain_summary: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
