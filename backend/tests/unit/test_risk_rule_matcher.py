from datetime import date

from app.domain.schemas.clause import ClauseLocation
from app.domain.schemas.clause_type import ClauseType
from app.domain.schemas.extracted_clause import ExtractedClause
from app.domain.schemas.risk_level import RiskLevel
from app.domain.schemas.risk_rule import RiskRule
from app.domain.services.risk_rule_matcher import match_rules


def _clause(clause_type: ClauseType, text: str) -> ExtractedClause:
    return ExtractedClause(
        clause_id="c-1",
        clause_type=clause_type,
        original_text=text,
        location=ClauseLocation(source_start_index=0, source_end_index=0, paragraph_ids=["p-0001"]),
        plain_summary="摘要",
        confidence=0.9,
    )


def _rule(
    clause_types: ClauseType | list[ClauseType],
    trigger_patterns: list[str],
    *,
    status: str = "reviewed",
    rule_id: str = "rule-1",
) -> RiskRule:
    return RiskRule(
        id=rule_id,
        version=1,
        jurisdiction="TW",
        clause_types=[clause_types] if isinstance(clause_types, ClauseType) else clause_types,
        topic="測試主題",
        trigger_patterns=trigger_patterns,
        risk_for_client=RiskLevel.LOW,
        risk_for_vendor=RiskLevel.HIGH,
        risk_explanation="說明",
        suggestion_template="建議",
        status=status,
        updated_at=date(2026, 8, 23),
    )


def test_matches_when_clause_type_and_trigger_pattern_both_hit():
    clause = _clause(ClauseType.PAYMENT, "總價款為新臺幣一百萬元整，分三期支付。")
    rule = _rule(ClauseType.PAYMENT, ["新臺幣"])
    assert match_rules(clause, [rule]) == [rule]


def test_no_match_when_clause_type_differs():
    clause = _clause(ClauseType.SCOPE, "乙方應完成系統開發。")
    rule = _rule(ClauseType.PAYMENT, ["開發"])
    assert match_rules(clause, [rule]) == []


def test_no_match_when_trigger_pattern_absent():
    clause = _clause(ClauseType.PAYMENT, "總價款為新臺幣一百萬元整。")
    rule = _rule(ClauseType.PAYMENT, ["逾期違約金"])
    assert match_rules(clause, [rule]) == []


def test_matches_with_fullwidth_normalization():
    clause = _clause(ClauseType.PAYMENT, "總價款為１００元。")
    rule = _rule(ClauseType.PAYMENT, ["100元"])
    assert match_rules(clause, [rule]) == [rule]


def test_returns_all_matching_rules_for_multiple_candidates():
    clause = _clause(ClauseType.PAYMENT, "新臺幣一百萬元，分期支付百分之三十。")
    rule_a = _rule(ClauseType.PAYMENT, ["新臺幣"], rule_id="rule-a")
    rule_b = _rule(ClauseType.PAYMENT, ["百分之"], rule_id="rule-b")
    rule_c = _rule(ClauseType.PAYMENT, ["逾期違約金"], rule_id="rule-c")
    assert match_rules(clause, [rule_a, rule_b, rule_c]) == [rule_a, rule_b]


def test_caller_is_responsible_for_filtering_status_and_jurisdiction():
    # match_rules does not filter by status/jurisdiction itself — callers
    # must pass only RiskRuleRepository.list_reviewed() output.
    clause = _clause(ClauseType.PAYMENT, "新臺幣一百萬元。")
    draft_rule = _rule(ClauseType.PAYMENT, ["新臺幣"], status="draft")
    assert match_rules(clause, [draft_rule]) == [draft_rule]


def test_matches_when_clause_type_is_any_of_rules_multiple_types():
    # Real-world finding: 001 splits by 條 (article), and one article can
    # bundle multiple topics under a single 002 clause_type label (e.g. a
    # "交付方式與委製費用" article whose last item is actually about the
    # acceptance deadline, but 002 classifies the whole article as payment).
    clause = _clause(ClauseType.PAYMENT, "甲方應於乙方完成後無限期進行驗收，如有不通過應立即改善。")
    rule = _rule([ClauseType.ACCEPTANCE, ClauseType.PAYMENT], ["無限期進行驗收"])
    assert match_rules(clause, [rule]) == [rule]


def test_no_match_when_clause_type_not_in_any_of_rules_types():
    clause = _clause(ClauseType.SCOPE, "乙方應完成系統開發，無限期進行驗收。")
    rule = _rule([ClauseType.ACCEPTANCE, ClauseType.PAYMENT], ["無限期進行驗收"])
    assert match_rules(clause, [rule]) == []
