from __future__ import annotations

_DIGITS = {"零": 0, "〇": 0, "一": 1, "二": 2, "兩": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
_UNITS = {"十": 10, "百": 100, "千": 1000}
_BIG_UNITS = {"萬": 10_000, "億": 100_000_000}


def parse_chinese_numeral(text: str) -> float | None:
    """Converts a run of Chinese numeral characters (e.g. 一百萬, 三十) to its
    numeric value. Returns None if `text` contains anything else. Used so
    "百分之三十" and "30%" can be compared as the same value — see
    specs/002-llm-clause-classification/spec.md 決策 3 and the false-positive
    this fixes (LLM commonly rewrites 中文數字 as 阿拉伯數字 without changing
    the actual amount)."""
    if not text:
        return None

    total = 0
    section = 0
    num = 0
    for ch in text:
        if ch in _DIGITS:
            num = _DIGITS[ch]
        elif ch in _UNITS:
            unit = _UNITS[ch]
            section += (num or 1) * unit
            num = 0
        elif ch in _BIG_UNITS:
            section += num
            total += section * _BIG_UNITS[ch]
            section = 0
            num = 0
        else:
            return None
    total += section + num
    return float(total)
