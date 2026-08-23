from __future__ import annotations

from pathlib import Path

from app.domain.entities.document import Document
from app.domain.schemas.extracted_clause import ExtractedClause
from app.domain.schemas.risk_assessment import RiskAssessment, ReviewReport
from app.domain.schemas.risk_level import RiskLevel

DISCLAIMER = "本服務僅提供輔助審閱與風險提示，非法律意見。"


def build_review_report(
    document: Document, clauses: list[ExtractedClause], risks: list[RiskAssessment]
) -> ReviewReport:
    """Pure Python, deterministic — no LLM call (spec.md FR10)."""
    contract_title = Path(document.filename).stem or document.document_id

    high_client = sum(1 for r in risks if r.risk_for_client == RiskLevel.HIGH)
    high_vendor = sum(1 for r in risks if r.risk_for_vendor == RiskLevel.HIGH)
    overall_summary = (
        f"本文件共 {len(clauses)} 個條款，其中 {len(risks)} 項標記風險"
        f"（甲方高風險 {high_client} 項、乙方高風險 {high_vendor} 項）。"
    )

    return ReviewReport(
        document_id=document.document_id,
        contract_title=contract_title,
        overall_summary=overall_summary,
        disclaimer=DISCLAIMER,
        clauses=clauses,
        risks=risks,
    )
