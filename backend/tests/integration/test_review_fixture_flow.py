import json
from pathlib import Path

import jsonschema

from app.application.commands.review_document import ReviewDocumentCommand
from app.domain.entities.document import Document, DocumentStatus
from app.domain.schemas.llm_risk_assessment import LLMEvidenceItem, RiskAssessmentResult
from app.domain.schemas.risk_level import RiskLevel
from app.domain.schemas.risk_rule import RiskRule
from app.domain.services.clause_splitter import split_into_clauses
from app.domain.services.review_report_builder import build_review_report
from app.infrastructure.docx.block_reader import compute_checksum, open_docx, read_source_blocks
from app.infrastructure.repositories.json_risk_rule_repository import JsonRiskRuleRepository
from app.infrastructure.repositories.memory_repository import (
    InMemoryClauseClassificationRepository,
    InMemoryDocumentRepository,
    InMemoryRiskAssessmentRepository,
)
from tests.fakes.fake_knowledge_repository import FakeKnowledgeRepository
from tests.fakes.fake_risk_assessment_provider import FakeRiskAssessmentProvider
from tests.fakes.fake_risk_judge_provider import FakeRiskJudgeProvider

FIXTURES_001 = Path(__file__).resolve().parents[3] / "specs" / "001-docx-clause-extraction" / "fixtures"
TEST_RULES_PATH = (
    Path(__file__).resolve().parents[3]
    / "specs"
    / "003-dual-perspective-risk-review"
    / "fixtures"
    / "reviewed_test_rules.json"
)
SCHEMA_PATH = (
    Path(__file__).resolve().parents[3]
    / "specs"
    / "003-dual-perspective-risk-review"
    / "contracts"
    / "review_report.schema.json"
)


def _classified_clauses_from_fixture(filename: str):
    """Reuses 001's parser directly and stands in for 002's LLM classification
    step by assigning a plausible clause_type per clause deterministically —
    avoids a real/fake classification pass just to get test data."""
    from app.domain.schemas.clause_type import ClauseType
    from app.domain.schemas.extracted_clause import ExtractedClause

    content = (FIXTURES_001 / filename).read_bytes()
    checksum = compute_checksum(content)
    docx = open_docx(content)
    blocks = read_source_blocks(docx)
    parsed_clauses = split_into_clauses(blocks, checksum)

    type_by_article = {
        "第一條": ClauseType.SCOPE,
        "第二條": ClauseType.ACCEPTANCE,
        "第三條": ClauseType.PAYMENT,
    }
    extracted = []
    for clause in parsed_clauses:
        clause_type = type_by_article.get(clause.location.article_no, ClauseType.OTHER)
        extracted.append(
            ExtractedClause(
                clause_id=clause.clause_id,
                clause_type=clause_type,
                original_text=clause.original_text,
                location=clause.location,
                plain_summary="測試摘要",
                confidence=0.9,
                model_id="test-model",
            )
        )
    return extracted, checksum


def _applicable_for(clause_id: str, quote: str) -> RiskAssessmentResult:
    return RiskAssessmentResult(
        applicable=True,
        risk_for_client=RiskLevel.LOW,
        risk_for_vendor=RiskLevel.HIGH,
        concern="可能有疑慮，建議確認。",
        suggestion="可考慮協商調整。",
        evidence=[LLMEvidenceItem(quote=quote, rationale="原文依據")],
        confidence=0.85,
    )


def test_review_flow_matches_review_report_schema():
    clauses, checksum = _classified_clauses_from_fixture("normal-numbering.docx")
    rules: list[RiskRule] = JsonRiskRuleRepository(TEST_RULES_PATH).list_reviewed()
    assert rules  # sanity: test fixture rules loaded

    document_id = "review-fixture-doc"
    document_repository = InMemoryDocumentRepository()
    classification_repository = InMemoryClauseClassificationRepository()
    risk_assessment_repository = InMemoryRiskAssessmentRepository()

    document_repository.create(
        Document(
            document_id=document_id,
            filename="normal-numbering.docx",
            checksum=checksum,
            status=DocumentStatus.CLASSIFIED,
        )
    )
    classification_repository.replace_for_document(document_id, clauses)

    def default_result(request):
        # Applicable for every matched (clause, rule) pair, quoting a
        # substring that is guaranteed present in that clause's own text.
        clause = next(c for c in clauses if c.clause_id == request.clause_id)
        for candidate in ["追加報價", "視為驗收合格", "新臺幣", "百分之"]:
            if candidate in clause.original_text:
                return _applicable_for(request.clause_id, candidate)
        raise AssertionError("no groundable quote found for test setup")

    llm = FakeRiskAssessmentProvider(default_result_factory=default_result)

    class _StaticRuleRepo:
        def list_reviewed(self, jurisdiction: str = "TW") -> list[RiskRule]:
            return rules

    command = ReviewDocumentCommand(
        document_repository=document_repository,
        classification_repository=classification_repository,
        risk_rule_repository=_StaticRuleRepo(),
        risk_assessment_repository=risk_assessment_repository,
        risk_provider=llm,
        knowledge_repository=FakeKnowledgeRepository(),
        judge_provider=FakeRiskJudgeProvider(),
    )
    document = command.execute(document_id)
    assert document.status == DocumentStatus.COMPLETED

    risks = risk_assessment_repository.list_for_document(document_id)
    assert risks  # at least one clause matched a test rule

    report = build_review_report(document, clauses, risks)
    schema = json.loads(SCHEMA_PATH.read_text())
    jsonschema.validate(instance=json.loads(report.model_dump_json()), schema=schema)

    for risk in risks:
        clause = next(c for c in clauses if c.clause_id == risk.clause_id)
        for evidence in risk.evidence:
            assert evidence.quote in clause.original_text
