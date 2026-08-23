from __future__ import annotations

import threading

from app.domain.entities.document import Document, DocumentStatus
from app.domain.schemas.clause import ParsedClause


class InMemoryDocumentRepository:
    """MVP DocumentRepository adapter; replaced by a PostgreSQL adapter in
    feature 006 without changing application command call sites (design.md).
    """

    def __init__(self) -> None:
        self._documents: dict[str, Document] = {}
        self._lock = threading.Lock()

    def create(self, document: Document) -> Document:
        with self._lock:
            self._documents[document.document_id] = document
        return document

    def get(self, document_id: str) -> Document | None:
        with self._lock:
            return self._documents.get(document_id)

    def set_status(self, document_id: str, status: DocumentStatus, error_code: str | None = None) -> None:
        with self._lock:
            document = self._documents.get(document_id)
            if document is None:
                return
            updated = document.model_copy(update={"status": status, "error_code": error_code})
            self._documents[document_id] = updated


class InMemoryClauseRepository:
    def __init__(self) -> None:
        self._clauses: dict[str, list[ParsedClause]] = {}
        self._lock = threading.Lock()

    def replace_for_document(self, document_id: str, clauses: list[ParsedClause]) -> None:
        with self._lock:
            self._clauses[document_id] = list(clauses)

    def list_for_document(self, document_id: str) -> list[ParsedClause]:
        with self._lock:
            return list(self._clauses.get(document_id, []))
