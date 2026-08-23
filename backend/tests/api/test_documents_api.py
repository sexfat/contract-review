import json
from io import BytesIO
from pathlib import Path

import jsonschema
import pytest
from docx import Document
from docx.oxml.ns import qn
from fastapi.testclient import TestClient

from app.main import app

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "specs" / "001-docx-clause-extraction" / "fixtures"
SCHEMA_PATH = (
    Path(__file__).resolve().parents[3]
    / "specs"
    / "001-docx-clause-extraction"
    / "contracts"
    / "clause.schema.json"
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _upload_and_parse(client: TestClient, filename: str) -> str:
    content = (FIXTURES_DIR / filename).read_bytes()
    upload_response = client.post(
        "/api/documents",
        files={"file": (filename, content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert upload_response.status_code == 201
    document_id = upload_response.json()["document_id"]

    parse_response = client.post(f"/api/documents/{document_id}/parse")
    assert parse_response.status_code == 202
    assert parse_response.json()["status"] == "parsing"
    return document_id


def test_full_upload_parse_clauses_flow_matches_schema(client: TestClient):
    document_id = _upload_and_parse(client, "normal-numbering.docx")

    response = client.get(f"/api/documents/{document_id}/clauses")
    assert response.status_code == 200

    body = response.json()
    schema = json.loads(SCHEMA_PATH.read_text())
    jsonschema.validate(instance=body, schema=schema)
    assert len(body["clauses"]) >= 3


def test_reject_non_docx_extension(client: TestClient):
    response = client.post(
        "/api/documents",
        files={"file": ("contract.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )
    assert response.status_code == 400
    assert response.json()["error_code"] == "UNSUPPORTED_FILE_TYPE"


def test_reject_docx_extension_with_non_zip_content(client: TestClient):
    response = client.post(
        "/api/documents",
        files={
            "file": (
                "fake.docx",
                b"this is not a real zip/docx payload",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    assert response.status_code == 400
    assert response.json()["error_code"] == "UNSUPPORTED_FILE_TYPE"


def test_reject_wrong_declared_mime_type(client: TestClient):
    content = (FIXTURES_DIR / "normal-numbering.docx").read_bytes()
    response = client.post(
        "/api/documents",
        files={"file": ("normal-numbering.docx", content, "application/pdf")},
    )
    assert response.status_code == 400
    assert response.json()["error_code"] == "UNSUPPORTED_FILE_TYPE"


def test_reject_unreadable_docx_at_upload_time(client: TestClient):
    real_content = (FIXTURES_DIR / "normal-numbering.docx").read_bytes()
    truncated = real_content[:200]  # keeps PK signature + early marker, breaks zip structure
    response = client.post(
        "/api/documents",
        files={
            "file": (
                "broken.docx",
                truncated,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    assert response.status_code == 400
    assert response.json()["error_code"] in {"UNSUPPORTED_FILE_TYPE", "INVALID_DOCX"}


def test_failed_document_preserves_specific_error_message(client: TestClient):
    document = Document()
    paragraph = document.add_paragraph("第一條　工作範圍")
    ins = paragraph._p.makeelement(qn("w:ins"), {})
    paragraph._p.append(ins)
    buffer = BytesIO()
    document.save(buffer)

    upload_response = client.post(
        "/api/documents",
        files={
            "file": (
                "tracked.docx",
                buffer.getvalue(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    assert upload_response.status_code == 201
    document_id = upload_response.json()["document_id"]

    parse_response = client.post(f"/api/documents/{document_id}/parse")
    assert parse_response.status_code == 400
    assert parse_response.json()["error_code"] == "TRACKED_CHANGES_NOT_SUPPORTED"

    clauses_response = client.get(f"/api/documents/{document_id}/clauses")
    assert clauses_response.status_code == 400
    body = clauses_response.json()
    assert body["error_code"] == "TRACKED_CHANGES_NOT_SUPPORTED"
    assert body["message"] == "文件含修訂追蹤，請先接受或拒絕修訂後重新上傳。"


def test_clauses_not_ready_before_parsing(client: TestClient):
    content = (FIXTURES_DIR / "normal-numbering.docx").read_bytes()
    upload_response = client.post(
        "/api/documents",
        files={"file": ("normal-numbering.docx", content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    document_id = upload_response.json()["document_id"]

    response = client.get(f"/api/documents/{document_id}/clauses")
    assert response.status_code == 409
    assert response.json()["error_code"] == "DOCUMENT_NOT_READY"


def test_clauses_for_unknown_document_returns_404(client: TestClient):
    response = client.get("/api/documents/does-not-exist/clauses")
    assert response.status_code == 404
    assert response.json()["error_code"] == "DOCUMENT_NOT_FOUND"


def test_health_endpoint_ok(client: TestClient):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.parametrize("filename", ["normal-numbering.docx", "mixed-numbering.docx", "payment-table.docx"])
def test_reparsing_document_id_is_stable_across_two_uploads(client: TestClient, filename: str):
    first_id = _upload_and_parse(client, filename)
    first_clauses = client.get(f"/api/documents/{first_id}/clauses").json()["clauses"]

    second_id = _upload_and_parse(client, filename)
    second_clauses = client.get(f"/api/documents/{second_id}/clauses").json()["clauses"]

    assert [c["clause_id"] for c in first_clauses] == [c["clause_id"] for c in second_clauses]
