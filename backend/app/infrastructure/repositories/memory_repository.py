from __future__ import annotations

import threading

from app.domain.entities.document import Document, DocumentStatus
from app.domain.schemas.clause import ParsedClause
from app.domain.schemas.extracted_clause import ExtractedClause
from app.domain.schemas.risk_assessment import RiskAssessment


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


class InMemoryClauseClassificationRepository:
    """Kept separate from InMemoryClauseRepository so 001's storage/contract
    is never touched by 002 (design.md "回滾方式")."""

    def __init__(self) -> None:
        self._clauses: dict[str, list[ExtractedClause]] = {}
        self._lock = threading.Lock()

    def replace_for_document(self, document_id: str, clauses: list[ExtractedClause]) -> None:
        with self._lock:
            self._clauses[document_id] = list(clauses)

    def list_for_document(self, document_id: str) -> list[ExtractedClause]:
        with self._lock:
            return list(self._clauses.get(document_id, []))


class InMemoryRiskAssessmentRepository:
    """Kept separate from 001/002's repositories so 003 cannot corrupt their
    data (design.md "回滾方式")."""

    def __init__(self) -> None:
        self._risks: dict[str, list[RiskAssessment]] = {}
        self._lock = threading.Lock()

    def replace_for_document(self, document_id: str, risks: list[RiskAssessment]) -> None:
        with self._lock:
            self._risks[document_id] = list(risks)

    def list_for_document(self, document_id: str) -> list[RiskAssessment]:
        with self._lock:
            return list(self._risks.get(document_id, []))
