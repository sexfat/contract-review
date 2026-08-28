from __future__ import annotations

from pydantic import BaseModel, Field

from app.domain.schemas.clause_type import ClauseType
from app.domain.schemas.retrieval import RetrievedKnowledge
from app.domain.schemas.risk_level import RiskLevel


class RiskAssessmentRequest(BaseModel):
    """One LLM call per (clause, matched rule) pair — see design.md
    "設計決策". source_refs is deliberately absent: the application layer
    sets it deterministically to [rule_id, *retrieved knowledge_id] rather
    than trusting LLM output (specs/005-rag-and-judge-gate/spec.md FR5)."""

    clause_id: str = Field(min_length=1)
    clause_type: ClauseType
    original_text: str = Field(min_length=1)
    rule_id: str = Field(min_length=1)
    rule_topic: str = Field(min_length=1)
    rule_risk_explanation: str = Field(min_length=1)
    rule_review_questions: list[str] = []
    rule_suggestion_template: str = Field(min_length=1)
    retrieved_sources: list[RetrievedKnowledge] = []


class LLMEvidenceItem(BaseModel):
    quote: str = Field(min_length=1)
    rationale: str


class RiskAssessmentResult(BaseModel):
    applicable: bool
    risk_for_client: RiskLevel
    risk_for_vendor: RiskLevel
    concern: str = Field(min_length=1)
    suggestion: str = Field(min_length=1)
    evidence: list[LLMEvidenceItem] = []
    confidence: float = Field(ge=0, le=1)
