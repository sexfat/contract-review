from __future__ import annotations

from pydantic import BaseModel, Field

from app.domain.schemas.llm_risk_assessment import LLMEvidenceItem
from app.domain.schemas.retrieval import RetrievedKnowledge
from app.domain.schemas.risk_level import RiskLevel


class JudgeRequest(BaseModel):
    """Only carries what judge actually needs to decide — deliberately not
    the whole RiskAssessmentResult (e.g. `applicable` is meaningless here:
    judge only runs after 003's deterministic checks already passed on an
    applicable=true result). See design.md "設計決策"."""

    clause_original_text: str = Field(min_length=1)
    risk_for_client: RiskLevel
    risk_for_vendor: RiskLevel
    concern: str = Field(min_length=1)
    suggestion: str = Field(min_length=1)
    evidence: list[LLMEvidenceItem]
    retrieved_sources: list[RetrievedKnowledge] = []


class JudgeResult(BaseModel):
    passed: bool
    reason: str = Field(min_length=1)
