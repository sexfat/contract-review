from __future__ import annotations

from pydantic import BaseModel, Field

from app.domain.schemas.clause_type import ClauseType
from app.domain.schemas.extracted_clause import ExtractedClause
from app.domain.schemas.risk_level import RiskLevel


class EvidenceRef(BaseModel):
    clause_id: str = Field(min_length=1)
    quote: str = Field(min_length=1)
    rationale: str


class RiskAssessment(BaseModel):
    """DEVELOPMENT_SPEC.md §7 RiskAssessment, unmodified — unlike
    ExtractedClause (002), no extra fields are needed here."""

    risk_id: str = Field(min_length=1)
    clause_id: str = Field(min_length=1)
    clause_type: ClauseType
    risk_for_client: RiskLevel
    risk_for_vendor: RiskLevel
    concern: str = Field(min_length=1)
    suggestion: str = Field(min_length=1)
    evidence: list[EvidenceRef] = Field(min_length=1)
    source_refs: list[str] = []
    confidence: float = Field(ge=0, le=1)
    requires_human_review: bool = False


class ReviewReport(BaseModel):
    document_id: str = Field(min_length=1)
    contract_title: str = Field(min_length=1)
    overall_summary: str = Field(min_length=1)
    disclaimer: str = Field(min_length=1)
    clauses: list[ExtractedClause]
    risks: list[RiskAssessment]
