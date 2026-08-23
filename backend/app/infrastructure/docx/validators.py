from __future__ import annotations

from app.domain.errors import FileTooLargeError, UnsupportedFileTypeError
from app.infrastructure.docx.block_reader import MAX_FILE_SIZE_BYTES

_DOCX_ZIP_SIGNATURE = b"PK\x03\x04"
_DOCX_CONTENT_TYPES_MARKER = b"[Content_Types].xml"
_DOCX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
# Some clients (curl, Postman, older browsers) send a generic binary MIME
# type instead of the OOXML one; tolerate that but reject an overtly wrong
# declared type (e.g. application/pdf) per DEVELOPMENT_SPEC.md #12.
_ALLOWED_CONTENT_TYPES = {_DOCX_MIME_TYPE, "application/octet-stream", "", None}


def validate_upload(filename: str, content: bytes, content_type: str | None = None) -> None:
    if not filename.lower().endswith(".docx"):
        raise UnsupportedFileTypeError()

    if content_type not in _ALLOWED_CONTENT_TYPES:
        raise UnsupportedFileTypeError()

    if len(content) > MAX_FILE_SIZE_BYTES:
        raise FileTooLargeError()

    if not content.startswith(_DOCX_ZIP_SIGNATURE):
        raise UnsupportedFileTypeError()

    if _DOCX_CONTENT_TYPES_MARKER not in content:
        raise UnsupportedFileTypeError()
