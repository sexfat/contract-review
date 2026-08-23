from __future__ import annotations

from fastapi import APIRouter, Depends, UploadFile
from fastapi import File as FastAPIFile

from app.api.dependencies import (
    get_clauses_query,
    get_parse_document_command,
    get_upload_document_command,
)
from app.api.schemas import DocumentStatusResponse
from app.application.commands.parse_document import ParseDocumentCommand
from app.application.commands.upload_document import UploadDocumentCommand
from app.application.queries.get_clauses import GetClausesQuery
from app.domain.entities.document import DocumentStatus
from app.domain.schemas.clause import ClauseListResponse

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("", status_code=201, response_model=DocumentStatusResponse)
async def upload_document(
    file: UploadFile = FastAPIFile(...),
    command: UploadDocumentCommand = Depends(get_upload_document_command),
) -> DocumentStatusResponse:
    content = await file.read()
    document = command.execute(filename=file.filename or "", content=content, content_type=file.content_type)
    return DocumentStatusResponse(document_id=document.document_id, status=document.status)


@router.post("/{document_id}/parse", status_code=202, response_model=DocumentStatusResponse)
async def parse_document(
    document_id: str,
    command: ParseDocumentCommand = Depends(get_parse_document_command),
) -> DocumentStatusResponse:
    # spec.md API contract: 202 always reports status=parsing, even though the
    # local MVP executes synchronously — callers must poll GET .../clauses
    # for the actual outcome, so the response contract stays stable once this
    # becomes a background job.
    command.execute(document_id)
    return DocumentStatusResponse(document_id=document_id, status=DocumentStatus.PARSING)


@router.get("/{document_id}/clauses", response_model=ClauseListResponse)
async def get_clauses(
    document_id: str,
    query: GetClausesQuery = Depends(get_clauses_query),
) -> ClauseListResponse:
    return query.execute(document_id)
