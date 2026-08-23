from __future__ import annotations

from dataclasses import dataclass

from app.application.ports.clause_classification_repository import ClauseClassificationRepository
from app.application.ports.clause_repository import ClauseRepository
from app.application.ports.document_repository import DocumentRepository
from app.domain.entities.document import DocumentStatus
from app.domain.errors import DocumentNotFoundError, DocumentNotReadyError, error_for_code
from app.domain.schemas.clause import ClauseListResponse
from app.domain.schemas.extracted_clause import ClassifiedClauseListResponse

_NOT_READY_STATUSES = (DocumentStatus.UPLOADED, DocumentStatus.PARSING, DocumentStatus.CLASSIFYING)


@dataclass
class GetClausesQuery:
    document_repository: DocumentRepository
    clause_repository: ClauseRepository
    classification_repository: ClauseClassificationRepository

    def execute(self, document_id: str) -> ClauseListResponse | ClassifiedClauseListResponse:
        document = self.document_repository.get(document_id)
        if document is None:
            raise DocumentNotFoundError()

        if document.status in _NOT_READY_STATUSES:
            raise DocumentNotReadyError()

        if document.status == DocumentStatus.FAILED:
            raise error_for_code(document.error_code or "INVALID_DOCX")

        if document.status == DocumentStatus.CLASSIFIED:
            clauses = self.classification_repository.list_for_document(document_id)
            return ClassifiedClauseListResponse(document_id=document_id, status="classified", clauses=clauses)

        # status == PARSED: 001's original shape, untouched.
        clauses = self.clause_repository.list_for_document(document_id)
        return ClauseListResponse(document_id=document_id, status="parsed", clauses=clauses)
