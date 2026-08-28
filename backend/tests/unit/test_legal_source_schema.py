import json
from pathlib import Path

import jsonschema

_REPO_ROOT = Path(__file__).resolve().parents[3]
SEED_PATH = _REPO_ROOT / "data" / "legal_sources.seed.json"
SCHEMA_PATH = _REPO_ROOT / "specs" / "005-rag-and-judge-gate" / "contracts" / "legal_source.schema.json"
EXAMPLE_FIXTURE_PATH = (
    _REPO_ROOT / "specs" / "005-rag-and-judge-gate" / "fixtures" / "example_legal_sources.json"
)


def test_legal_sources_seed_matches_schema():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    data = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(instance=data, schema=schema)
    assert len(data) >= 10  # spec.md 驗收條件 9


def test_example_fixture_matches_schema():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    data = json.loads(EXAMPLE_FIXTURE_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(instance=data, schema=schema)
