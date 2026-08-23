from __future__ import annotations

from dataclasses import dataclass

from app.application.ports.clause_repository import ClauseRepository
from app.application.ports.document_repository import DocumentRepository
from app.domain.entities.document import DocumentStatus
from app.domain.errors import DocumentNotFoundError, DocumentNotReadyError, error_for_code
from app.domain.schemas.clause import ClauseListResponse


@dataclass
class GetClausesQuery:
    document_repository: DocumentRepository
    clause_repository: ClauseRepository

    def execute(self, document_id: str) -> ClauseListResponse:
        document = self.document_repository.get(document_id)
        if document is None:
            raise DocumentNotFoundError()

        if document.status in (DocumentStatus.UPLOADED, DocumentStatus.PARSING):
            raise DocumentNotReadyError()

        if document.status == DocumentStatus.FAILED:
            raise error_for_code(document.error_code or "INVALID_DOCX")

        clauses = self.clause_repository.list_for_document(document_id)
        return ClauseListResponse(document_id=document_id, status="parsed", clauses=clauses)
