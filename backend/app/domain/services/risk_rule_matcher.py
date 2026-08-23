from __future__ import annotations

from app.domain.schemas.extracted_clause import ExtractedClause
from app.domain.schemas.risk_rule import RiskRule
from app.domain.services.text_normalize import normalize


def match_rules(clause: ExtractedClause, rules: list[RiskRule]) -> list[RiskRule]:
    """Deterministic, pure-Python candidate matching: same clause_type AND at
    least one trigger_pattern substring found in the clause's original_text
    (after full/half-width normalization). Callers must pass only
    `status == "reviewed"` rules — this function does not filter by status.

    A match here is only a *candidate* — real applicability is judged by the
    LLM via RiskAssessmentResult.applicable (see
    specs/003-dual-perspective-risk-review/design.md), since substring
    matching is coarse and can false-positive."""
    normalized_text = normalize(clause.original_text)
    matched: list[RiskRule] = []
    for rule in rules:
        if rule.clause_type != clause.clause_type:
            continue
        if any(normalize(pattern) in normalized_text for pattern in rule.trigger_patterns):
            matched.append(rule)
    return matched
