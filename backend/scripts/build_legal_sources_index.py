"""Offline index build: reads data/legal_sources.seed.json, embeds each
entry's own content (not parent-expanded — see chunking policy in
specs/005-rag-and-judge-gate/spec.md), and writes
data/legal_sources.embeddings.npz.

Not part of the API request/startup path — run manually whenever
legal_sources.seed.json changes:

    cd backend && uv run python scripts/build_legal_sources_index.py

Requires OLLAMA_EMBEDDING_MODEL and OLLAMA_EMBEDDING_BASE_URL in .env.
Ollama Cloud hosts no embedding models (confirmed live against
ollama.com/search?c=cloud), so this points at a *local* Ollama daemon —
run `ollama serve` and `ollama pull qwen3-embedding:0.6b` (or whichever
model OLLAMA_EMBEDDING_MODEL names) before running this script."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.infrastructure.llm.config import load_llm_settings  # noqa: E402
from app.infrastructure.llm.ollama_embedding_provider import OllamaEmbeddingProvider  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[2]
SEED_PATH = _REPO_ROOT / "data" / "legal_sources.seed.json"
EMBEDDINGS_PATH = _REPO_ROOT / "data" / "legal_sources.embeddings.npz"


def main() -> None:
    settings = load_llm_settings()
    if settings.ollama_embedding_model is None:
        raise SystemExit(
            "OLLAMA_EMBEDDING_MODEL is not set in .env — confirm an available "
            "embedding model before building the index (see "
            "specs/005-rag-and-judge-gate/spec.md 待人工完成事項)."
        )
    provider = OllamaEmbeddingProvider(settings)

    sources = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    vectors = {entry["knowledge_id"]: provider.embed([entry["content"]])[0] for entry in sources}

    np.savez(EMBEDDINGS_PATH, **{kid: np.asarray(vec, dtype=np.float32) for kid, vec in vectors.items()})
    print(f"wrote {len(vectors)} vectors to {EMBEDDINGS_PATH}")


if __name__ == "__main__":
    main()
