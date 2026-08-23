import json
from pathlib import Path

import jsonschema
import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_classification_repository,
    get_classify_clauses_command,
    get_clause_repository,
    get_document_repository,
    get_review_document_command,
    get_review_report_query,
    get_risk_assessment_repository,
)
from app.application.commands.classify_clauses import ClassifyClausesCommand
from app.application.commands.review_document import ReviewDocumentCommand
from app.application.queries.get_review_report import GetReviewReportQuery
from app.domain.errors import LLMProviderUnavailableError
from app.domain.schemas.clause_type import ClauseType
from app.domain.schemas.llm_classification import LLMClassificationResult
from app.domain.schemas.llm_risk_assessment import LLMEvidenceItem, RiskAssessmentResult
from app.domain.schemas.risk_level import RiskLevel
from app.domain.schemas.risk_rule import RiskRule
from app.infrastructure.repositories.json_risk_rule_repository import JsonRiskRuleRepository
from app.main import app
from tests.fakes.fake_llm_provider import FakeLLMProvider
from tests.fakes.fake_risk_assessment_provider import FakeRiskAssessmentProvider

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "specs" / "001-docx-clause-extraction" / "fixtures"
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


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


class _StaticRiskRuleRepository:
    def __init__(self, rules: list[RiskRule]) -> None:
        self._rules = rules

    def list_reviewed(self, jurisdiction: str = "TW") -> list[RiskRule]:
        return self._rules


def _classify_result_for(request) -> LLMClassificationResult:
    text = request.original_text
    if "驗收合格" in text:
        clause_type = ClauseType.ACCEPTANCE
    elif "新臺幣" in text or "百分之" in text:
        clause_type = ClauseType.PAYMENT
    elif "追加報價" in text:
        clause_type = ClauseType.SCOPE
    else:
        clause_type = ClauseType.OTHER
    return LLMClassificationResult(
        clause_id=request.clause_id, clause_type=clause_type, plain_summary="測試摘要", confidence=0.9
    )


def _upload_parse_classify(client: TestClient, filename: str) -> str:
    content = (FIXTURES_DIR / filename).read_bytes()
    upload_response = client.post(
        "/api/documents",
        files={"file": (filename, content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    document_id = upload_response.json()["document_id"]
    client.post(f"/api/documents/{document_id}/parse")

    app.dependency_overrides[get_classify_clauses_command] = lambda: ClassifyClausesCommand(
        document_repository=get_document_repository(),
        clause_repository=get_clause_repository(),
        classification_repository=get_classification_repository(),
        llm_provider=FakeLLMProvider(default_result_factory=_classify_result_for),
    )
    client.post(f"/api/documents/{document_id}/classify")
    return document_id


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


def _override_review_provider(risk_provider: FakeRiskAssessmentProvider, rules: list[RiskRule]) -> None:
    app.dependency_overrides[get_review_document_command] = lambda: ReviewDocumentCommand(
        document_repository=get_document_repository(),
        classification_repository=get_classification_repository(),
        risk_rule_repository=_StaticRiskRuleRepository(rules),
        risk_assessment_repository=get_risk_assessment_repository(),
        risk_provider=risk_provider,
    )
    app.dependency_overrides[get_review_report_query] = lambda: GetReviewReportQuery(
        document_repository=get_document_repository(),
        classification_repository=get_classification_repository(),
        risk_assessment_repository=get_risk_assessment_repository(),
    )


def test_review_flow_matches_review_report_schema(client: TestClient):
    document_id = _upload_parse_classify(client, "normal-numbering.docx")
    rules = JsonRiskRuleRepository(TEST_RULES_PATH).list_reviewed()

    def default_result(request):
        for candidate in ["追加報價", "視為驗收合格", "新臺幣", "百分之"]:
            if candidate in request.original_text:
                return _applicable_for(request.clause_id, candidate)
        raise AssertionError("no groundable quote found for test setup")

    _override_review_provider(FakeRiskAssessmentProvider(default_result_factory=default_result), rules)

    review_response = client.post(f"/api/documents/{document_id}/review")
    assert review_response.status_code == 202
    assert review_response.json()["status"] == "reviewing"

    report_response = client.get(f"/api/documents/{document_id}/report")
    assert report_response.status_code == 200
    body = report_response.json()

    schema = json.loads(SCHEMA_PATH.read_text())
    jsonschema.validate(instance=body, schema=schema)
    assert body["risks"]
    assert "非法律意見" in body["disclaimer"]


def test_review_before_classify_is_document_not_ready(client: TestClient):
    content = (FIXTURES_DIR / "normal-numbering.docx").read_bytes()
    upload_response = client.post(
        "/api/documents",
        files={"file": ("normal-numbering.docx", content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    document_id = upload_response.json()["document_id"]
    client.post(f"/api/documents/{document_id}/parse")
    _override_review_provider(FakeRiskAssessmentProvider(), [])

    response = client.post(f"/api/documents/{document_id}/review")
    assert response.status_code == 409
    assert response.json()["error_code"] == "DOCUMENT_NOT_READY"


def test_review_unknown_document_returns_404(client: TestClient):
    _override_review_provider(FakeRiskAssessmentProvider(), [])
    response = client.post("/api/documents/does-not-exist/review")
    assert response.status_code == 404
    assert response.json()["error_code"] == "DOCUMENT_NOT_FOUND"


def test_report_not_ready_before_review(client: TestClient):
    document_id = _upload_parse_classify(client, "normal-numbering.docx")
    _override_review_provider(FakeRiskAssessmentProvider(), [])

    response = client.get(f"/api/documents/{document_id}/report")
    assert response.status_code == 409
    assert response.json()["error_code"] == "DOCUMENT_NOT_READY"


def test_llm_provider_unavailable_returns_502_and_report_reflects_failure(client: TestClient):
    document_id = _upload_parse_classify(client, "normal-numbering.docx")
    rules = JsonRiskRuleRepository(TEST_RULES_PATH).list_reviewed()

    def _always_unavailable(request):
        raise LLMProviderUnavailableError()

    _override_review_provider(FakeRiskAssessmentProvider(default_result_factory=_always_unavailable), rules)

    review_response = client.post(f"/api/documents/{document_id}/review")
    assert review_response.status_code == 502
    assert review_response.json()["error_code"] == "LLM_PROVIDER_UNAVAILABLE"

    report_response = client.get(f"/api/documents/{document_id}/report")
    assert report_response.status_code == 502
    assert report_response.json()["error_code"] == "LLM_PROVIDER_UNAVAILABLE"


def test_get_clauses_still_returns_classified_shape_after_completed(client: TestClient):
    document_id = _upload_parse_classify(client, "normal-numbering.docx")
    rules = JsonRiskRuleRepository(TEST_RULES_PATH).list_reviewed()
    _override_review_provider(FakeRiskAssessmentProvider(default_result_factory=lambda req: RiskAssessmentResult(
        applicable=False,
        risk_for_client=RiskLevel.NONE,
        risk_for_vendor=RiskLevel.NONE,
        concern="不適用",
        suggestion="不適用",
        evidence=[],
        confidence=0.5,
    )), rules)

    client.post(f"/api/documents/{document_id}/review")

    clauses_response = client.get(f"/api/documents/{document_id}/clauses")
    assert clauses_response.status_code == 200
    assert clauses_response.json()["status"] == "classified"
