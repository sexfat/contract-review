from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class DocumentStatus(str, Enum):
    UPLOADED = "uploaded"
    PARSING = "parsing"
    PARSED = "parsed"
    FAILED = "failed"


class Document(BaseModel):
    document_id: str
    filename: str
    checksum: str
    status: DocumentStatus
    error_code: str | None = None
