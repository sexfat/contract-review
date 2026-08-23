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
)
from app.application.commands.classify_clauses import ClassifyClausesCommand
from app.domain.errors import LLMProviderUnavailableError
from app.domain.schemas.clause_type import ClauseType
from app.domain.schemas.llm_classification import LLMClassificationResult
from app.main import app
from tests.fakes.fake_llm_provider import FakeLLMProvider

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "specs" / "001-docx-clause-extraction" / "fixtures"
SCHEMA_PATH = (
    Path(__file__).resolve().parents[3]
    / "specs"
    / "002-llm-clause-classification"
    / "contracts"
    / "extracted_clause.schema.json"
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def _override_llm_provider(llm: FakeLLMProvider) -> None:
    app.dependency_overrides[get_classify_clauses_command] = lambda: ClassifyClausesCommand(
        document_repository=get_document_repository(),
        clause_repository=get_clause_repository(),
        classification_repository=get_classification_repository(),
        llm_provider=llm,
    )


def _upload_and_parse(client: TestClient, filename: str) -> str:
    content = (FIXTURES_DIR / filename).read_bytes()
    upload_response = client.post(
        "/api/documents",
        files={"file": (filename, content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    document_id = upload_response.json()["document_id"]
    client.post(f"/api/documents/{document_id}/parse")
    return document_id


def _reasonable_result(clause_id: str) -> LLMClassificationResult:
    return LLMClassificationResult(
        clause_id=clause_id,
        clause_type=ClauseType.SCOPE,
        plain_summary="本條款經過分析後的白話摘要。",
        confidence=0.9,
    )


def test_classify_flow_matches_extracted_clause_schema(client: TestClient):
    document_id = _upload_and_parse(client, "normal-numbering.docx")
    _override_llm_provider(FakeLLMProvider(default_result_factory=lambda req: _reasonable_result(req.clause_id)))

    classify_response = client.post(f"/api/documents/{document_id}/classify")
    assert classify_response.status_code == 202
    assert classify_response.json()["status"] == "classifying"

    clauses_response = client.get(f"/api/documents/{document_id}/clauses")
    assert clauses_response.status_code == 200
    body = clauses_response.json()
    assert body["status"] == "classified"

    schema = json.loads(SCHEMA_PATH.read_text())
    jsonschema.validate(instance=body, schema=schema)
    assert all(c["clause_type"] == "scope" for c in body["clauses"])
    assert all(c["requires_human_review"] is False for c in body["clauses"])


def test_classify_before_parse_is_document_not_ready(client: TestClient):
    content = (FIXTURES_DIR / "normal-numbering.docx").read_bytes()
    upload_response = client.post(
        "/api/documents",
        files={"file": ("normal-numbering.docx", content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    document_id = upload_response.json()["document_id"]
    _override_llm_provider(FakeLLMProvider())

    response = client.post(f"/api/documents/{document_id}/classify")
    assert response.status_code == 409
    assert response.json()["error_code"] == "DOCUMENT_NOT_READY"


def test_classify_unknown_document_returns_404(client: TestClient):
    _override_llm_provider(FakeLLMProvider())
    response = client.post("/api/documents/does-not-exist/classify")
    assert response.status_code == 404
    assert response.json()["error_code"] == "DOCUMENT_NOT_FOUND"


def test_llm_provider_unavailable_returns_502_and_get_clauses_reflects_failure(client: TestClient):
    document_id = _upload_and_parse(client, "normal-numbering.docx")

    def _always_unavailable(request):
        raise LLMProviderUnavailableError()

    _override_llm_provider(FakeLLMProvider(default_result_factory=_always_unavailable))

    classify_response = client.post(f"/api/documents/{document_id}/classify")
    assert classify_response.status_code == 502
    assert classify_response.json()["error_code"] == "LLM_PROVIDER_UNAVAILABLE"

    clauses_response = client.get(f"/api/documents/{document_id}/clauses")
    assert clauses_response.status_code == 502
    assert clauses_response.json()["error_code"] == "LLM_PROVIDER_UNAVAILABLE"


def test_get_clauses_still_matches_001_shape_when_only_parsed(client: TestClient):
    document_id = _upload_and_parse(client, "normal-numbering.docx")

    response = client.get(f"/api/documents/{document_id}/clauses")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "parsed"
    assert all(c["clause_type"] == "other" for c in body["clauses"])
    assert all("plain_summary" not in c for c in body["clauses"])
