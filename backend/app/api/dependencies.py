from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from app.application.commands.classify_clauses import ClassifyClausesCommand
from app.application.commands.parse_document import ParseDocumentCommand
from app.application.commands.upload_document import UploadDocumentCommand
from app.application.ports.llm_provider import LLMProvider
from app.application.queries.get_clauses import GetClausesQuery
from app.infrastructure.llm.config import load_llm_settings
from app.infrastructure.llm.ollama_provider import OllamaClassificationProvider
from app.infrastructure.repositories.memory_repository import (
    InMemoryClauseClassificationRepository,
    InMemoryClauseRepository,
    InMemoryDocumentRepository,
)
from app.infrastructure.storage.local_file_storage import LocalFileStorage

_STORAGE_DIR = Path(__file__).resolve().parents[2] / "var" / "documents"


@lru_cache
def get_document_repository() -> InMemoryDocumentRepository:
    return InMemoryDocumentRepository()


@lru_cache
def get_clause_repository() -> InMemoryClauseRepository:
    return InMemoryClauseRepository()


@lru_cache
def get_classification_repository() -> InMemoryClauseClassificationRepository:
    return InMemoryClauseClassificationRepository()


@lru_cache
def get_file_storage() -> LocalFileStorage:
    return LocalFileStorage(_STORAGE_DIR)


@lru_cache
def get_llm_provider() -> LLMProvider:
    # Raises pydantic's ValidationError if OLLAMA_API_KEY is unset — fail
    # fast on first /classify call rather than silently misbehaving later.
    settings = load_llm_settings()
    return OllamaClassificationProvider(settings)


def get_upload_document_command() -> UploadDocumentCommand:
    return UploadDocumentCommand(
        document_repository=get_document_repository(),
        file_storage=get_file_storage(),
    )


def get_parse_document_command() -> ParseDocumentCommand:
    return ParseDocumentCommand(
        document_repository=get_document_repository(),
        clause_repository=get_clause_repository(),
        file_storage=get_file_storage(),
    )


def get_classify_clauses_command() -> ClassifyClausesCommand:
    return ClassifyClausesCommand(
        document_repository=get_document_repository(),
        clause_repository=get_clause_repository(),
        classification_repository=get_classification_repository(),
        llm_provider=get_llm_provider(),
    )


def get_clauses_query() -> GetClausesQuery:
    return GetClausesQuery(
        document_repository=get_document_repository(),
        clause_repository=get_clause_repository(),
        classification_repository=get_classification_repository(),
    )
