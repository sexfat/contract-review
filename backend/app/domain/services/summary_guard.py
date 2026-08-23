from __future__ import annotations

import re

from app.domain.services.chinese_numeral import parse_chinese_numeral
from app.domain.services.text_normalize import normalize

# Percent/currency values are compared numerically (see chinese_numeral.py) so
# "百分之三十" (original) and "30%" (LLM's common Arabic-numeral paraphrase)
# are recognized as the same value instead of failing a literal substring
# check — observed live during spec.md AC2 manual review. Dates stay a
# literal substring check: format-only reformatting is a lower-frequency,
# lower-risk paraphrase and out of scope for this pass.
_PERCENT_ARABIC = re.compile(r"百分之\s*(\d[\d,]*(?:\.\d+)?)|(\d[\d,]*(?:\.\d+)?)\s*%")
_PERCENT_CHINESE = re.compile(r"百分之\s*([一二三四五六七八九十百千萬零〇兩]+)")
_CURRENCY_ARABIC = re.compile(r"(?:NT\$|新臺幣)?\s*(\d[\d,]*(?:\.\d+)?)\s*元")
_CURRENCY_ARABIC_PREFIXED = re.compile(r"(?:NT\$|新臺幣)\s*(\d[\d,]*(?:\.\d+)?)(?!\s*元)")
_CURRENCY_CHINESE = re.compile(r"([一二三四五六七八九十百千萬零〇兩]+)元")

_DATE_PATTERNS = [
    re.compile(r"(?:民國|西元)\s*\d{1,4}\s*年(?:\s*\d{1,2}\s*月(?:\s*\d{1,2}\s*日)?)?"),
    re.compile(r"\d{2,4}\s*年\s*\d{1,2}\s*月(?:\s*\d{1,2}\s*日)?"),
    re.compile(r"\d{4}/\d{1,2}/\d{1,2}"),
]


def _to_float(raw: str) -> float | None:
    try:
        return float(raw.replace(",", ""))
    except ValueError:
        return None


def _percent_matches(text: str) -> list[tuple[str, float]]:
    matches: list[tuple[str, float]] = []
    for match in _PERCENT_ARABIC.finditer(text):
        raw = next(g for g in match.groups() if g)
        value = _to_float(raw)
        if value is not None:
            matches.append((match.group(0), value))
    for match in _PERCENT_CHINESE.finditer(text):
        value = parse_chinese_numeral(match.group(1))
        if value is not None:
            matches.append((match.group(0), value))
    return matches


def _currency_matches(text: str) -> list[tuple[str, float]]:
    matches: list[tuple[str, float]] = []
    for match in _CURRENCY_ARABIC.finditer(text):
        value = _to_float(match.group(1))
        if value is not None:
            matches.append((match.group(0), value))
    for match in _CURRENCY_ARABIC_PREFIXED.finditer(text):
        value = _to_float(match.group(1))
        if value is not None:
            matches.append((match.group(0), value))
    for match in _CURRENCY_CHINESE.finditer(text):
        value = parse_chinese_numeral(match.group(1))
        if value is not None:
            matches.append((match.group(0), value))
    return matches


def find_ungrounded_amounts_and_dates(original_text: str, plain_summary: str) -> list[str]:
    """Return the amount/percent/date substrings in plain_summary that
    cannot be grounded in original_text. Amounts/percentages are compared by
    numeric value (Chinese-numeral <-> Arabic-numeral paraphrases count as
    grounded); dates are compared as literal substrings (after full/half-width
    normalization). An empty list means the summary passed the check."""
    normalized_original = normalize(original_text)
    normalized_summary = normalize(plain_summary)

    ungrounded: list[str] = []

    grounded_percents = {v for _, v in _percent_matches(normalized_original)}
    for raw, value in _percent_matches(normalized_summary):
        if value not in grounded_percents:
            ungrounded.append(raw)

    grounded_currency = {v for _, v in _currency_matches(normalized_original)}
    for raw, value in _currency_matches(normalized_summary):
        if value not in grounded_currency:
            ungrounded.append(raw)

    for pattern in _DATE_PATTERNS:
        for match in pattern.finditer(normalized_summary):
            candidate = match.group(0)
            if candidate not in normalized_original:
                ungrounded.append(candidate)

    return ungrounded
