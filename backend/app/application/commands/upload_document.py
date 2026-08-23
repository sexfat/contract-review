from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.application.ports.document_repository import DocumentRepository
from app.application.ports.file_storage import FileStorage
from app.domain.entities.document import Document, DocumentStatus
from app.infrastructure.docx.block_reader import compute_checksum, open_docx
from app.infrastructure.docx.validators import validate_upload


@dataclass
class UploadDocumentCommand:
    document_repository: DocumentRepository
    file_storage: FileStorage

    def execute(self, filename: str, content: bytes, content_type: str | None = None) -> Document:
        validate_upload(filename, content, content_type)
        # Confirm the package actually opens as a Word document before we
        # accept it — spec.md's upload contract returns 400 for readability
        # problems, not just extension/MIME mismatches.
        open_docx(content)

        document_id = uuid.uuid4().hex
        checksum = compute_checksum(content)
        self.file_storage.save(document_id, content)

        document = Document(
            document_id=document_id,
            filename=filename,
            checksum=checksum,
            status=DocumentStatus.UPLOADED,
        )
        return self.document_repository.create(document)
