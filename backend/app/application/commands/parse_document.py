from __future__ import annotations

from dataclasses import dataclass

from app.application.ports.clause_repository import ClauseRepository
from app.application.ports.document_repository import DocumentRepository
from app.application.ports.file_storage import FileStorage
from app.domain.entities.document import Document, DocumentStatus
from app.domain.errors import DocumentNotFoundError, DomainError
from app.domain.services.clause_splitter import split_into_clauses
from app.infrastructure.docx.block_reader import (
    assert_no_tracked_changes,
    open_docx,
    read_source_blocks,
)


@dataclass
class ParseDocumentCommand:
    document_repository: DocumentRepository
    clause_repository: ClauseRepository
    file_storage: FileStorage

    def execute(self, document_id: str) -> Document:
        document = self.document_repository.get(document_id)
        if document is None:
            raise DocumentNotFoundError()

        self.document_repository.set_status(document_id, DocumentStatus.PARSING)

        try:
            content = self.file_storage.load(document_id)
            docx = open_docx(content)
            assert_no_tracked_changes(docx)
            blocks = read_source_blocks(docx)
            clauses = split_into_clauses(blocks, document.checksum)
        except DomainError as exc:
            self.document_repository.set_status(document_id, DocumentStatus.FAILED, exc.error_code)
            raise

        self.clause_repository.replace_for_document(document_id, clauses)
        self.document_repository.set_status(document_id, DocumentStatus.PARSED)

        parsed_document = self.document_repository.get(document_id)
        assert parsed_document is not None
        return parsed_document
