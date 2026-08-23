from __future__ import annotations

from typing import Protocol

from app.domain.schemas.llm_risk_assessment import RiskAssessmentRequest, RiskAssessmentResult


class RiskAssessmentProvider(Protocol):
    model_id: str

    def assess_risk(self, request: RiskAssessmentRequest) -> RiskAssessmentResult:
        """Raises LLMOutputInvalidError (retryable) or
        LLMProviderUnavailableError (fails the whole document review),
        same semantics as LLMProvider (002)."""
        ...
