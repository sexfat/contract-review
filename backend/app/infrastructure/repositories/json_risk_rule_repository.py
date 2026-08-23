from __future__ import annotations

import json
from pathlib import Path

from app.domain.schemas.risk_rule import RiskRule


class JsonRiskRuleRepository:
    """Loads data/risk_rules.seed.json once at construction. Entries are
    developer-authored data, not user input — an invalid entry fails fast
    rather than being silently skipped."""

    def __init__(self, path: Path) -> None:
        raw = json.loads(path.read_text(encoding="utf-8"))
        self._rules = [RiskRule.model_validate(entry) for entry in raw]

    def list_reviewed(self, jurisdiction: str = "TW") -> list[RiskRule]:
        return [r for r in self._rules if r.status == "reviewed" and r.jurisdiction == jurisdiction]
