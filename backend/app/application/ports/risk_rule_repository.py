from __future__ import annotations

from typing import Protocol

from app.domain.schemas.risk_rule import RiskRule


class RiskRuleRepository(Protocol):
    def list_reviewed(self, jurisdiction: str = "TW") -> list[RiskRule]: ...
