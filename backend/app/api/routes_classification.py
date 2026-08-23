from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import get_classify_clauses_command
from app.api.schemas import DocumentStatusResponse
from app.application.commands.classify_clauses import ClassifyClausesCommand
from app.domain.entities.document import DocumentStatus

router = APIRouter(prefix="/api/documents", tags=["classification"])


@router.post("/{document_id}/classify", status_code=202, response_model=DocumentStatusResponse)
async def classify_document(
    document_id: str,
    command: ClassifyClausesCommand = Depends(get_classify_clauses_command),
) -> DocumentStatusResponse:
    # Same 202-always-"classifying" contract as /parse (see routes_documents.py).
    command.execute(document_id)
    return DocumentStatusResponse(document_id=document_id, status=DocumentStatus.CLASSIFYING)
