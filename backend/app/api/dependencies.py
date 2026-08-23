from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from app.application.commands.parse_document import ParseDocumentCommand
from app.application.commands.upload_document import UploadDocumentCommand
from app.application.queries.get_clauses import GetClausesQuery
from app.infrastructure.repositories.memory_repository import (
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
def get_file_storage() -> LocalFileStorage:
    return LocalFileStorage(_STORAGE_DIR)


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


def get_clauses_query() -> GetClausesQuery:
    return GetClausesQuery(
        document_repository=get_document_repository(),
        clause_repository=get_clause_repository(),
    )
