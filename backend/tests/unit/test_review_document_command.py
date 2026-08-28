from datetime import date

import pytest

from app.application.commands.review_document import ReviewDocumentCommand
from app.domain.entities.document import Document, DocumentStatus
from app.domain.errors import (
    DocumentNotFoundError,
    DocumentNotReadyError,
    LLMOutputInvalidError,
    LLMProviderUnavailableError,
)
from app.domain.schemas.clause import ClauseLocation
from app.domain.schemas.clause_type import ClauseType
from app.domain.schemas.extracted_clause import ExtractedClause
from app.domain.schemas.judge import JudgeResult
from app.domain.schemas.llm_risk_assessment import LLMEvidenceItem, RiskAssessmentResult
from app.domain.schemas.retrieval import RetrievedKnowledge
from app.domain.schemas.risk_level import RiskLevel
from app.domain.schemas.risk_rule import RiskRule
from app.infrastructure.repositories.memory_repository import (
    InMemoryClauseClassificationRepository,
    InMemoryDocumentRepository,
    InMemoryRiskAssessmentRepository,
)
from tests.fakes.fake_knowledge_repository import FakeKnowledgeRepository
from tests.fakes.fake_risk_assessment_provider import FakeRiskAssessmentProvider
from tests.fakes.fake_risk_judge_provider import FakeRiskJudgeProvider

DOCUMENT_ID = "doc-1"


class _StaticRiskRuleRepository:
    def __init__(self, rules: list[RiskRule]) -> None:
        self._rules = rules

    def list_reviewed(self, jurisdiction: str = "TW") -> list[RiskRule]:
        return self._rules


def _clause(clause_id: str = "clause-1", text: str = "總價款為新臺幣一百萬元。") -> ExtractedClause:
    return ExtractedClause(
        clause_id=clause_id,
        clause_type=ClauseType.PAYMENT,
        original_text=text,
        location=ClauseLocation(source_start_index=0, source_end_index=0, paragraph_ids=["p-0001"]),
        plain_summary="摘要",
        confidence=0.9,
    )


def _rule(rule_id: str = "rule-1", trigger_patterns: list[str] | None = None) -> RiskRule:
    return RiskRule(
        id=rule_id,
        version=1,
        jurisdiction="TW",
        clause_types=[ClauseType.PAYMENT],
        topic="測試主題",
        trigger_patterns=trigger_patterns or ["新臺幣"],
        risk_for_client=RiskLevel.LOW,
        risk_for_vendor=RiskLevel.HIGH,
        risk_explanation="說明",
        suggestion_template="建議",
        status="reviewed",
        updated_at=date(2026, 8, 23),
    )


def _applicable_result(clause_id: str, quote: str = "新臺幣一百萬元") -> RiskAssessmentResult:
    return RiskAssessmentResult(
        applicable=True,
        risk_for_client=RiskLevel.LOW,
        risk_for_vendor=RiskLevel.HIGH,
        concern="可能有疑慮。",
        suggestion="建議確認。",
        evidence=[LLMEvidenceItem(quote=quote, rationale="說明")],
        confidence=0.8,
    )


def _make_command(
    risk_provider: FakeRiskAssessmentProvider,
    rules: list[RiskRule],
    *,
    status: DocumentStatus = DocumentStatus.CLASSIFIED,
    knowledge_repository: FakeKnowledgeRepository | None = None,
    judge_provider: FakeRiskJudgeProvider | None = None,
):
    document_repository = InMemoryDocumentRepository()
    classification_repository = InMemoryClauseClassificationRepository()
    risk_assessment_repository = InMemoryRiskAssessmentRepository()

    document_repository.create(
        Document(document_id=DOCUMENT_ID, filename="test.docx", checksum="abc", status=status)
    )

    command = ReviewDocumentCommand(
        document_repository=document_repository,
        classification_repository=classification_repository,
        risk_rule_repository=_StaticRiskRuleRepository(rules),
        risk_assessment_repository=risk_assessment_repository,
        risk_provider=risk_provider,
        knowledge_repository=knowledge_repository or FakeKnowledgeRepository(),
        judge_provider=judge_provider or FakeRiskJudgeProvider(),
    )
    return command, document_repository, classification_repository, risk_assessment_repository


def test_document_not_found_raises():
    command, *_ = _make_command(FakeRiskAssessmentProvider(), [])
    with pytest.raises(DocumentNotFoundError):
        command.execute("missing-doc")


def test_document_not_ready_for_uploaded_status():
    command, *_ = _make_command(FakeRiskAssessmentProvider(), [], status=DocumentStatus.UPLOADED)
    with pytest.raises(DocumentNotReadyError):
        command.execute(DOCUMENT_ID)


def test_no_matched_rule_produces_no_risk():
    clause = _clause(text="乙方應完成系統開發。")  # no rule trigger pattern matches
    rule = _rule(trigger_patterns=["新臺幣"])
    command, _, classification_repository, risk_assessment_repository = _make_command(
        FakeRiskAssessmentProvider(), [rule]
    )
    classification_repository.replace_for_document(DOCUMENT_ID, [clause])

    document = command.execute(DOCUMENT_ID)

    assert document.status == DocumentStatus.COMPLETED
    assert risk_assessment_repository.list_for_document(DOCUMENT_ID) == []


def test_applicable_result_produces_risk_assessment():
    clause = _clause()
    rule = _rule()
    llm = FakeRiskAssessmentProvider(script={(clause.clause_id, rule.id): [_applicable_result(clause.clause_id)]})
    command, _, classification_repository, risk_assessment_repository = _make_command(llm, [rule])
    classification_repository.replace_for_document(DOCUMENT_ID, [clause])

    document = command.execute(DOCUMENT_ID)

    assert document.status == DocumentStatus.COMPLETED
    [risk] = risk_assessment_repository.list_for_document(DOCUMENT_ID)
    assert risk.clause_id == clause.clause_id
    assert risk.source_refs == [rule.id]
    assert risk.evidence[0].quote == "新臺幣一百萬元"


def test_not_applicable_result_produces_no_risk_without_retry():
    clause = _clause()
    rule = _rule()
    not_applicable = RiskAssessmentResult(
        applicable=False,
        risk_for_client=RiskLevel.NONE,
        risk_for_vendor=RiskLevel.NONE,
        concern="不適用",
        suggestion="不適用",
        evidence=[],
        confidence=0.9,
    )
    llm = FakeRiskAssessmentProvider(script={(clause.clause_id, rule.id): [not_applicable]})
    command, _, classification_repository, risk_assessment_repository = _make_command(llm, [rule])
    classification_repository.replace_for_document(DOCUMENT_ID, [clause])

    command.execute(DOCUMENT_ID)

    assert risk_assessment_repository.list_for_document(DOCUMENT_ID) == []
    assert len(llm.calls) == 1  # applicable=False does not consume a retry


def test_ungrounded_evidence_retried_then_dropped():
    clause = _clause()
    rule = _rule()
    bad_result = _applicable_result(clause.clause_id, quote="原文沒有的金額")
    llm = FakeRiskAssessmentProvider(script={(clause.clause_id, rule.id): [bad_result, bad_result]})
    command, _, classification_repository, risk_assessment_repository = _make_command(llm, [rule])
    classification_repository.replace_for_document(DOCUMENT_ID, [clause])

    document = command.execute(DOCUMENT_ID)

    assert document.status == DocumentStatus.COMPLETED
    assert risk_assessment_repository.list_for_document(DOCUMENT_ID) == []
    assert len(llm.calls) == 2


def test_banned_phrase_retried_then_dropped():
    clause = _clause()
    rule = _rule()
    assertive_result = RiskAssessmentResult(
        applicable=True,
        risk_for_client=RiskLevel.LOW,
        risk_for_vendor=RiskLevel.HIGH,
        concern="本條無效。",
        suggestion="建議確認。",
        evidence=[LLMEvidenceItem(quote="新臺幣一百萬元", rationale="說明")],
        confidence=0.8,
    )
    llm = FakeRiskAssessmentProvider(script={(clause.clause_id, rule.id): [assertive_result, assertive_result]})
    command, _, classification_repository, risk_assessment_repository = _make_command(llm, [rule])
    classification_repository.replace_for_document(DOCUMENT_ID, [clause])

    command.execute(DOCUMENT_ID)

    assert risk_assessment_repository.list_for_document(DOCUMENT_ID) == []
    assert len(llm.calls) == 2


def test_retry_once_then_succeed():
    clause = _clause()
    rule = _rule()
    llm = FakeRiskAssessmentProvider(
        script={(clause.clause_id, rule.id): [LLMOutputInvalidError(), _applicable_result(clause.clause_id)]}
    )
    command, _, classification_repository, risk_assessment_repository = _make_command(llm, [rule])
    classification_repository.replace_for_document(DOCUMENT_ID, [clause])

    command.execute(DOCUMENT_ID)

    [risk] = risk_assessment_repository.list_for_document(DOCUMENT_ID)
    assert risk.clause_id == clause.clause_id


def test_llm_provider_unavailable_fails_whole_document_without_persisting():
    clause_a = _clause(clause_id="clause-1")
    clause_b = _clause(clause_id="clause-2")
    rule = _rule()
    llm = FakeRiskAssessmentProvider(script={("clause-1", rule.id): [LLMProviderUnavailableError()]})
    command, document_repository, classification_repository, risk_assessment_repository = _make_command(
        llm, [rule]
    )
    classification_repository.replace_for_document(DOCUMENT_ID, [clause_a, clause_b])

    with pytest.raises(LLMProviderUnavailableError):
        command.execute(DOCUMENT_ID)

    document = document_repository.get(DOCUMENT_ID)
    assert document.status == DocumentStatus.FAILED
    assert document.error_code == "LLM_PROVIDER_UNAVAILABLE"
    assert risk_assessment_repository.list_for_document(DOCUMENT_ID) == []


def _retrieved(knowledge_id: str = "civil-492") -> RetrievedKnowledge:
    return RetrievedKnowledge(
        knowledge_id=knowledge_id,
        parent_id=None,
        title="民法第492條",
        content="承攬人完成工作，應使其具備約定之品質...",
        source_url=None,
        effective_date=None,
        version=1,
    )


def test_no_matched_rule_does_not_trigger_retrieval():
    clause = _clause(text="乙方應完成系統開發。")  # no rule trigger pattern matches
    rule = _rule(trigger_patterns=["新臺幣"])
    knowledge_repository = FakeKnowledgeRepository([_retrieved()])
    command, _, classification_repository, _ = _make_command(
        FakeRiskAssessmentProvider(), [rule], knowledge_repository=knowledge_repository
    )
    classification_repository.replace_for_document(DOCUMENT_ID, [clause])

    command.execute(DOCUMENT_ID)

    assert knowledge_repository.calls == []


def test_matched_rule_triggers_retrieval_and_source_refs_include_knowledge_id():
    clause = _clause()
    rule = _rule()
    retrieved = _retrieved()
    llm = FakeRiskAssessmentProvider(script={(clause.clause_id, rule.id): [_applicable_result(clause.clause_id)]})
    knowledge_repository = FakeKnowledgeRepository([retrieved])
    command, _, classification_repository, risk_assessment_repository = _make_command(
        llm, [rule], knowledge_repository=knowledge_repository
    )
    classification_repository.replace_for_document(DOCUMENT_ID, [clause])

    command.execute(DOCUMENT_ID)

    assert len(knowledge_repository.calls) == 1
    [risk] = risk_assessment_repository.list_for_document(DOCUMENT_ID)
    assert risk.source_refs == [rule.id, retrieved.knowledge_id]


def test_judge_not_passed_retried_then_dropped():
    clause = _clause()
    rule = _rule()
    llm = FakeRiskAssessmentProvider(
        script={(clause.clause_id, rule.id): [_applicable_result(clause.clause_id), _applicable_result(clause.clause_id)]}
    )
    judge_provider = FakeRiskJudgeProvider(
        script={clause.original_text: [JudgeResult(passed=False, reason="超出原文支持"), JudgeResult(passed=False, reason="超出原文支持")]}
    )
    command, _, classification_repository, risk_assessment_repository = _make_command(
        llm, [rule], judge_provider=judge_provider
    )
    classification_repository.replace_for_document(DOCUMENT_ID, [clause])

    document = command.execute(DOCUMENT_ID)

    assert document.status == DocumentStatus.COMPLETED
    assert risk_assessment_repository.list_for_document(DOCUMENT_ID) == []
    assert len(judge_provider.calls) == 2


def test_judge_passed_after_retry_succeeds():
    clause = _clause()
    rule = _rule()
    llm = FakeRiskAssessmentProvider(
        script={(clause.clause_id, rule.id): [_applicable_result(clause.clause_id), _applicable_result(clause.clause_id)]}
    )
    judge_provider = FakeRiskJudgeProvider(
        script={clause.original_text: [JudgeResult(passed=False, reason="超出原文支持"), JudgeResult(passed=True, reason="通過")]}
    )
    command, _, classification_repository, risk_assessment_repository = _make_command(
        llm, [rule], judge_provider=judge_provider
    )
    classification_repository.replace_for_document(DOCUMENT_ID, [clause])

    command.execute(DOCUMENT_ID)

    [risk] = risk_assessment_repository.list_for_document(DOCUMENT_ID)
    assert risk.clause_id == clause.clause_id


def test_judge_provider_unavailable_fails_whole_document_without_persisting():
    clause_a = _clause(clause_id="clause-1")
    clause_b = _clause(clause_id="clause-2")
    rule = _rule()
    llm = FakeRiskAssessmentProvider(default_result_factory=lambda req: _applicable_result(req.clause_id))
    judge_provider = FakeRiskJudgeProvider(
        script={clause_a.original_text: [LLMProviderUnavailableError()]}
    )
    command, document_repository, classification_repository, risk_assessment_repository = _make_command(
        llm, [rule], judge_provider=judge_provider
    )
    classification_repository.replace_for_document(DOCUMENT_ID, [clause_a, clause_b])

    with pytest.raises(LLMProviderUnavailableError):
        command.execute(DOCUMENT_ID)

    document = document_repository.get(DOCUMENT_ID)
    assert document.status == DocumentStatus.FAILED
    assert document.error_code == "LLM_PROVIDER_UNAVAILABLE"
    assert risk_assessment_repository.list_for_document(DOCUMENT_ID) == []


def test_reviewing_document_allowed_when_already_completed():
    clause = _clause()
    rule = _rule()
    llm = FakeRiskAssessmentProvider(default_result_factory=lambda req: _applicable_result(req.clause_id))
    command, _, classification_repository, _ = _make_command(llm, [rule], status=DocumentStatus.COMPLETED)
    classification_repository.replace_for_document(DOCUMENT_ID, [clause])

    document = command.execute(DOCUMENT_ID)
    assert document.status == DocumentStatus.COMPLETED
