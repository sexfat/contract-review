from __future__ import annotations

from dataclasses import dataclass

from app.application.ports.clause_classification_repository import ClauseClassificationRepository
from app.application.ports.document_repository import DocumentRepository
from app.application.ports.risk_assessment_repository import RiskAssessmentRepository
from app.domain.entities.document import DocumentStatus
from app.domain.errors import DocumentNotFoundError, DocumentNotReadyError, error_for_code
from app.domain.schemas.risk_assessment import ReviewReport
from app.domain.services.review_report_builder import build_review_report


@dataclass
class GetReviewReportQuery:
    document_repository: DocumentRepository
    classification_repository: ClauseClassificationRepository
    risk_assessment_repository: RiskAssessmentRepository

    def execute(self, document_id: str) -> ReviewReport:
        document = self.document_repository.get(document_id)
        if document is None:
            raise DocumentNotFoundError()

        if document.status == DocumentStatus.FAILED:
            raise error_for_code(document.error_code or "INVALID_DOCX")

        if document.status != DocumentStatus.COMPLETED:
            raise DocumentNotReadyError()

        clauses = self.classification_repository.list_for_document(document_id)
        risks = self.risk_assessment_repository.list_for_document(document_id)
        return build_review_report(document, clauses, risks)
