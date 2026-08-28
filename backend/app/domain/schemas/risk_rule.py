from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from app.domain.schemas.clause_type import ClauseType
from app.domain.schemas.risk_level import RiskLevel


class RiskRule(BaseModel):
    """Mirrors data/risk_rules.seed.json's schema (DEVELOPMENT_SPEC.md §8).
    Only status == "reviewed" rules are usable by RiskRuleMatcher — see
    specs/003-dual-perspective-risk-review/spec.md 已確認決策 2.

    `clause_types` (plural, list) rather than a single ClauseType: 001's
    clause splitter groups by 條 (article), and a single article often
    bundles more than one topic under one heading (e.g. "交付方式與委製費用"
    covering both payment schedule and an acceptance-deadline sentence) —
    002 can only assign the clause one clause_type overall. A rule must be
    able to fire regardless of which of its relevant topics 002 picked as
    the primary label. See real-world finding recorded in
    specs/003-dual-perspective-risk-review/spec.md 已知限制."""

    id: str = Field(min_length=1)
    version: int
    jurisdiction: str
    clause_types: list[ClauseType] = Field(min_length=1)
    topic: str = Field(min_length=1)
    trigger_patterns: list[str] = Field(min_length=1)
    risk_for_client: RiskLevel
    risk_for_vendor: RiskLevel
    risk_explanation: str = Field(min_length=1)
    review_questions: list[str] = []
    suggestion_template: str = Field(min_length=1)
    source_refs: list[str] = []
    status: Literal["draft", "reviewed"]
    updated_at: date
