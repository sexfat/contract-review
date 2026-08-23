from __future__ import annotations

from typing import Protocol

from app.domain.schemas.extracted_clause import ExtractedClause


class ClauseClassificationRepository(Protocol):
    def replace_for_document(self, document_id: str, clauses: list[ExtractedClause]) -> None: ...

    def list_for_document(self, document_id: str) -> list[ExtractedClause]: ...
