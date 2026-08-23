from __future__ import annotations

from pathlib import Path


class LocalFileStorage:
    """Filesystem-backed FileStorage adapter for local MVP development."""

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, document_id: str) -> Path:
        return self._base_dir / f"{document_id}.docx"

    def save(self, document_id: str, content: bytes) -> None:
        self._path_for(document_id).write_bytes(content)

    def load(self, document_id: str) -> bytes:
        return self._path_for(document_id).read_bytes()

    def delete(self, document_id: str) -> None:
        path = self._path_for(document_id)
        if path.exists():
            path.unlink()
