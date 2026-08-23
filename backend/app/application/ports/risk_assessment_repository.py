from __future__ import annotations

from typing import Protocol

from app.domain.schemas.risk_assessment import RiskAssessment


class RiskAssessmentRepository(Protocol):
    def replace_for_document(self, document_id: str, risks: list[RiskAssessment]) -> None: ...

    def list_for_document(self, document_id: str) -> list[RiskAssessment]: ...
