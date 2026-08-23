from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import get_review_document_command, get_review_report_query
from app.api.schemas import DocumentStatusResponse
from app.application.commands.review_document import ReviewDocumentCommand
from app.application.queries.get_review_report import GetReviewReportQuery
from app.domain.entities.document import DocumentStatus
from app.domain.schemas.risk_assessment import ReviewReport

router = APIRouter(prefix="/api/documents", tags=["review"])


@router.post("/{document_id}/review", status_code=202, response_model=DocumentStatusResponse)
async def review_document(
    document_id: str,
    command: ReviewDocumentCommand = Depends(get_review_document_command),
) -> DocumentStatusResponse:
    # Same 202-always-"reviewing" contract as /parse and /classify.
    command.execute(document_id)
    return DocumentStatusResponse(document_id=document_id, status=DocumentStatus.REVIEWING)


@router.get("/{document_id}/report", response_model=ReviewReport)
async def get_review_report(
    document_id: str,
    query: GetReviewReportQuery = Depends(get_review_report_query),
) -> ReviewReport:
    return query.execute(document_id)
