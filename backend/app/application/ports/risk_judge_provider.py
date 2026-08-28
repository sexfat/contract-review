from __future__ import annotations

from typing import Protocol

from app.domain.schemas.judge import JudgeRequest, JudgeResult


class RiskJudgeProvider(Protocol):
    model_id: str

    def judge(self, request: JudgeRequest) -> JudgeResult:
        """Raises LLMOutputInvalidError (retryable) or
        LLMProviderUnavailableError (fails the whole document review), same
        semantics as RiskAssessmentProvider."""
        ...
