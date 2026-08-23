import json
from pathlib import Path

import jsonschema
import pytest

from app.application.commands.classify_clauses import ClassifyClausesCommand
from app.domain.entities.document import Document, DocumentStatus
from app.domain.schemas.clause_type import ClauseType
from app.domain.schemas.llm_classification import LLMClassificationResult
from app.domain.services.clause_splitter import split_into_clauses
from app.infrastructure.docx.block_reader import compute_checksum, open_docx, read_source_blocks
from app.infrastructure.repositories.memory_repository import (
    InMemoryClauseClassificationRepository,
    InMemoryClauseRepository,
    InMemoryDocumentRepository,
)
from tests.fakes.fake_llm_provider import FakeLLMProvider

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "specs" / "001-docx-clause-extraction" / "fixtures"
SCHEMA_PATH = (
    Path(__file__).resolve().parents[3]
    / "specs"
    / "002-llm-clause-classification"
    / "contracts"
    / "extracted_clause.schema.json"
)


def _reasonable_result(clause_id: str, original_text: str) -> LLMClassificationResult:
    return LLMClassificationResult(
        clause_id=clause_id,
        clause_type=ClauseType.SCOPE,
        plain_summary=(original_text[:20] + "（摘要）"),
        confidence=0.85,
    )


@pytest.mark.parametrize("filename", ["normal-numbering.docx", "mixed-numbering.docx", "payment-table.docx"])
def test_classification_preserves_001_clause_identity_and_matches_schema(filename: str):
    content = (FIXTURES_DIR / filename).read_bytes()
    checksum = compute_checksum(content)
    docx = open_docx(content)
    blocks = read_source_blocks(docx)
    parsed_clauses = split_into_clauses(blocks, checksum)

    document_id = "fixture-doc"
    document_repository = InMemoryDocumentRepository()
    clause_repository = InMemoryClauseRepository()
    classification_repository = InMemoryClauseClassificationRepository()

    document_repository.create(
        Document(document_id=document_id, filename=filename, checksum=checksum, status=DocumentStatus.PARSED)
    )
    clause_repository.replace_for_document(document_id, parsed_clauses)

    llm = FakeLLMProvider(
        default_result_factory=lambda req: _reasonable_result(req.clause_id, req.original_text)
    )
    command = ClassifyClausesCommand(
        document_repository=document_repository,
        clause_repository=clause_repository,
        classification_repository=classification_repository,
        llm_provider=llm,
    )

    document = command.execute(document_id)
    assert document.status == DocumentStatus.CLASSIFIED

    extracted = classification_repository.list_for_document(document_id)
    assert [c.clause_id for c in extracted] == [c.clause_id for c in parsed_clauses]
    assert [c.location for c in extracted] == [c.location for c in parsed_clauses]
    assert [c.original_text for c in extracted] == [c.original_text for c in parsed_clauses]

    response_body = {
        "document_id": document_id,
        "status": "classified",
        "clauses": [json.loads(c.model_dump_json()) for c in extracted],
    }
    schema = json.loads(SCHEMA_PATH.read_text())
    jsonschema.validate(instance=response_body, schema=schema)
