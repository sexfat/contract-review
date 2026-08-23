from __future__ import annotations

from typing import Protocol


class FileStorage(Protocol):
    def save(self, document_id: str, content: bytes) -> None: ...

    def load(self, document_id: str) -> bytes: ...

    def delete(self, document_id: str) -> None: ...
