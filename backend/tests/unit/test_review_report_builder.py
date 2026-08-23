from app.domain.entities.document import Document, DocumentStatus
from app.domain.schemas.clause import ClauseLocation
from app.domain.schemas.clause_type import ClauseType
from app.domain.schemas.extracted_clause import ExtractedClause
from app.domain.schemas.risk_assessment import EvidenceRef, RiskAssessment
from app.domain.schemas.risk_level import RiskLevel
from app.domain.services.review_report_builder import DISCLAIMER, build_review_report


def _clause(clause_id: str) -> ExtractedClause:
    return ExtractedClause(
        clause_id=clause_id,
        clause_type=ClauseType.PAYMENT,
        original_text="總價款為新臺幣一百萬元。",
        location=ClauseLocation(source_start_index=0, source_end_index=0, paragraph_ids=["p-0001"]),
        plain_summary="總價款為一百萬元。",
        confidence=0.9,
    )


def _risk(clause_id: str, *, risk_for_client: RiskLevel, risk_for_vendor: RiskLevel) -> RiskAssessment:
    return RiskAssessment(
        risk_id=f"risk-{clause_id}",
        clause_id=clause_id,
        clause_type=ClauseType.PAYMENT,
        risk_for_client=risk_for_client,
        risk_for_vendor=risk_for_vendor,
        concern="可能有疑慮。",
        suggestion="建議確認。",
        evidence=[EvidenceRef(clause_id=clause_id, quote="新臺幣一百萬元", rationale="說明")],
        confidence=0.8,
    )


def test_contract_title_uses_filename_stem():
    document = Document(document_id="doc-1", filename="測試合約.docx", checksum="abc", status=DocumentStatus.COMPLETED)
    report = build_review_report(document, [], [])
    assert report.contract_title == "測試合約"


def test_disclaimer_is_always_the_fixed_constant():
    document = Document(document_id="doc-1", filename="a.docx", checksum="abc", status=DocumentStatus.COMPLETED)
    report = build_review_report(document, [], [])
    assert report.disclaimer == DISCLAIMER
    assert "非法律意見" in report.disclaimer


def test_overall_summary_reflects_clause_and_risk_counts():
    document = Document(document_id="doc-1", filename="a.docx", checksum="abc", status=DocumentStatus.COMPLETED)
    clauses = [_clause("c-1"), _clause("c-2")]
    risks = [
        _risk("c-1", risk_for_client=RiskLevel.HIGH, risk_for_vendor=RiskLevel.LOW),
        _risk("c-2", risk_for_client=RiskLevel.LOW, risk_for_vendor=RiskLevel.HIGH),
    ]
    report = build_review_report(document, clauses, risks)
    assert "2 個條款" in report.overall_summary
    assert "2 項標記風險" in report.overall_summary
    assert "甲方高風險 1 項" in report.overall_summary
    assert "乙方高風險 1 項" in report.overall_summary


def test_zero_risks_still_produces_valid_report():
    document = Document(document_id="doc-1", filename="a.docx", checksum="abc", status=DocumentStatus.COMPLETED)
    report = build_review_report(document, [_clause("c-1")], [])
    assert report.risks == []
    assert "0 項標記風險" in report.overall_summary
