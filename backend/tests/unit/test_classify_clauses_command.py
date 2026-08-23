import pytest

from app.application.commands.classify_clauses import ClassifyClausesCommand
from app.domain.entities.document import Document, DocumentStatus
from app.domain.errors import (
    DocumentNotFoundError,
    DocumentNotReadyError,
    LLMOutputInvalidError,
    LLMProviderUnavailableError,
)
from app.domain.schemas.clause import ClauseLocation, ParsedClause
from app.domain.schemas.clause_type import ClauseType
from app.domain.schemas.llm_classification import LLMClassificationResult
from app.infrastructure.repositories.memory_repository import (
    InMemoryClauseClassificationRepository,
    InMemoryClauseRepository,
    InMemoryDocumentRepository,
)
from tests.fakes.fake_llm_provider import FakeLLMProvider

DOCUMENT_ID = "doc-1"


def _location(order: int) -> ClauseLocation:
    return ClauseLocation(source_start_index=order, source_end_index=order, paragraph_ids=[f"p-{order:04d}"])


def _parsed_clause(clause_id: str, order: int = 0, text: str = "乙方應完成系統開發。") -> ParsedClause:
    return ParsedClause(clause_id=clause_id, clause_type="other", original_text=text, location=_location(order))


def _valid_result(clause_id: str) -> LLMClassificationResult:
    return LLMClassificationResult(
        clause_id=clause_id,
        clause_type=ClauseType.SCOPE,
        plain_summary="乙方需完成系統開發工作。",
        confidence=0.9,
    )


def _make_command(llm_provider: FakeLLMProvider, status: DocumentStatus = DocumentStatus.PARSED):
    document_repository = InMemoryDocumentRepository()
    clause_repository = InMemoryClauseRepository()
    classification_repository = InMemoryClauseClassificationRepository()

    document_repository.create(
        Document(document_id=DOCUMENT_ID, filename="test.docx", checksum="abc", status=status)
    )

    command = ClassifyClausesCommand(
        document_repository=document_repository,
        clause_repository=clause_repository,
        classification_repository=classification_repository,
        llm_provider=llm_provider,
    )
    return command, document_repository, clause_repository, classification_repository


def test_document_not_found_raises():
    command, *_ = _make_command(FakeLLMProvider())
    with pytest.raises(DocumentNotFoundError):
        command.execute("missing-doc")


def test_document_not_ready_raises_for_uploaded_status():
    command, document_repository, _, _ = _make_command(FakeLLMProvider(), status=DocumentStatus.UPLOADED)
    with pytest.raises(DocumentNotReadyError):
        command.execute(DOCUMENT_ID)


def test_successful_classification_on_first_attempt():
    clause = _parsed_clause("clause-1")
    llm = FakeLLMProvider(script={"clause-1": [_valid_result("clause-1")]})
    command, _, clause_repository, classification_repository = _make_command(llm)
    clause_repository.replace_for_document(DOCUMENT_ID, [clause])

    document = command.execute(DOCUMENT_ID)

    assert document.status == DocumentStatus.CLASSIFIED
    [extracted] = classification_repository.list_for_document(DOCUMENT_ID)
    assert extracted.clause_type == ClauseType.SCOPE
    assert extracted.requires_human_review is False
    assert extracted.confidence == 0.9
    assert extracted.clause_id == "clause-1"
    assert extracted.location == clause.location


def test_retry_once_then_succeed():
    clause = _parsed_clause("clause-1")
    llm = FakeLLMProvider(
        script={"clause-1": [LLMOutputInvalidError(), _valid_result("clause-1")]}
    )
    command, _, clause_repository, classification_repository = _make_command(llm)
    clause_repository.replace_for_document(DOCUMENT_ID, [clause])

    document = command.execute(DOCUMENT_ID)

    assert document.status == DocumentStatus.CLASSIFIED
    [extracted] = classification_repository.list_for_document(DOCUMENT_ID)
    assert extracted.requires_human_review is False
    assert len(llm.calls) == 2


def test_two_failures_fall_back_to_requires_human_review():
    clause = _parsed_clause("clause-1")
    llm = FakeLLMProvider(
        script={"clause-1": [LLMOutputInvalidError(), LLMOutputInvalidError()]}
    )
    command, _, clause_repository, classification_repository = _make_command(llm)
    clause_repository.replace_for_document(DOCUMENT_ID, [clause])

    document = command.execute(DOCUMENT_ID)

    assert document.status == DocumentStatus.CLASSIFIED
    [extracted] = classification_repository.list_for_document(DOCUMENT_ID)
    assert extracted.requires_human_review is True
    assert extracted.confidence == 0.0
    assert extracted.clause_type == ClauseType.OTHER
    assert extracted.original_text == clause.original_text  # 未遺失原文


def test_ungrounded_summary_is_treated_as_invalid_and_retried():
    clause = _parsed_clause("clause-1", text="乙方應完成系統開發。")
    bad_result = LLMClassificationResult(
        clause_id="clause-1",
        clause_type=ClauseType.SCOPE,
        plain_summary="乙方應於一百萬元內完成開發。",  # 原文沒有這個金額
        confidence=0.8,
    )
    llm = FakeLLMProvider(script={"clause-1": [bad_result, _valid_result("clause-1")]})
    command, _, clause_repository, classification_repository = _make_command(llm)
    clause_repository.replace_for_document(DOCUMENT_ID, [clause])

    command.execute(DOCUMENT_ID)

    [extracted] = classification_repository.list_for_document(DOCUMENT_ID)
    assert extracted.requires_human_review is False
    assert extracted.plain_summary == "乙方需完成系統開發工作。"


def test_llm_provider_unavailable_fails_whole_document_without_persisting():
    clause_a = _parsed_clause("clause-1", order=0)
    clause_b = _parsed_clause("clause-2", order=1)
    llm = FakeLLMProvider(script={"clause-1": [LLMProviderUnavailableError()]})
    command, document_repository, clause_repository, classification_repository = _make_command(llm)
    clause_repository.replace_for_document(DOCUMENT_ID, [clause_a, clause_b])

    with pytest.raises(LLMProviderUnavailableError):
        command.execute(DOCUMENT_ID)

    document = document_repository.get(DOCUMENT_ID)
    assert document.status == DocumentStatus.FAILED
    assert document.error_code == "LLM_PROVIDER_UNAVAILABLE"
    assert classification_repository.list_for_document(DOCUMENT_ID) == []


def test_reclassify_allowed_when_already_classified():
    clause = _parsed_clause("clause-1")
    llm = FakeLLMProvider(default_result_factory=lambda req: _valid_result(req.clause_id))
    command, _, clause_repository, _ = _make_command(llm, status=DocumentStatus.CLASSIFIED)
    clause_repository.replace_for_document(DOCUMENT_ID, [clause])

    document = command.execute(DOCUMENT_ID)
    assert document.status == DocumentStatus.CLASSIFIED
