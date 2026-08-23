from __future__ import annotations

from pydantic import BaseModel

from app.domain.entities.document import DocumentStatus


class DocumentStatusResponse(BaseModel):
    document_id: str
    status: DocumentStatus


class ErrorResponse(BaseModel):
    error_code: str
    message: str
