from __future__ import annotations

from typing import Protocol

from app.domain.schemas.clause import ParsedClause


class ClauseRepository(Protocol):
    def replace_for_document(self, document_id: str, clauses: list[ParsedClause]) -> None: ...

    def list_for_document(self, document_id: str) -> list[ParsedClause]: ...
