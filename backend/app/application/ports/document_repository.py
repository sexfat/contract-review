from __future__ import annotations

from typing import Protocol

from app.domain.entities.document import Document, DocumentStatus


class DocumentRepository(Protocol):
    def create(self, document: Document) -> Document: ...

    def get(self, document_id: str) -> Document | None: ...

    def set_status(self, document_id: str, status: DocumentStatus, error_code: str | None = None) -> None: ...
