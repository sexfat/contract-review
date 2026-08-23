from __future__ import annotations

import re
import unicodedata

# Amounts: Arabic numerals anchored by EITHER a prefix marker (NT$/新臺幣) OR
# a suffix marker (元/%), so "NT$1,000" (no trailing 元) and "1,000元" (no
# prefix) both count; 百分之 followed by either Arabic or Chinese numerals;
# Chinese-numeral amounts ending in 元. Dates: 年/月/日, 民國/西元, and
# slash-separated forms. See specs/002-llm-clause-classification/design.md
# "白話摘要防呆".
_AMOUNT_PATTERNS = [
    re.compile(r"(?:NT\$|新臺幣)\s*\d[\d,]*(?:\.\d+)?(?:\s*元)?"),
    re.compile(r"\d[\d,]*(?:\.\d+)?\s*(?:元|%)"),
    re.compile(r"百分之\s*\d[\d,]*(?:\.\d+)?"),
    re.compile(r"百分之[一二三四五六七八九十百千萬]+"),
    re.compile(r"[一二三四五六七八九十百千萬]+元"),
]
_DATE_PATTERNS = [
    re.compile(r"(?:民國|西元)\s*\d{1,4}\s*年(?:\s*\d{1,2}\s*月(?:\s*\d{1,2}\s*日)?)?"),
    re.compile(r"\d{2,4}\s*年\s*\d{1,2}\s*月(?:\s*\d{1,2}\s*日)?"),
    re.compile(r"\d{4}/\d{1,2}/\d{1,2}"),
]

_ALL_PATTERNS = _AMOUNT_PATTERNS + _DATE_PATTERNS


def _normalize(text: str) -> str:
    # Full-width digits/punctuation -> half-width, so "１００元" matches "100元".
    return unicodedata.normalize("NFKC", text)


def find_ungrounded_amounts_and_dates(original_text: str, plain_summary: str) -> list[str]:
    """Return the amount/date substrings in plain_summary that cannot be
    found in original_text (after full/half-width normalization). An empty
    list means the summary passed the grounding check."""
    normalized_original = _normalize(original_text)
    normalized_summary = _normalize(plain_summary)

    ungrounded: list[str] = []
    for pattern in _ALL_PATTERNS:
        for match in pattern.finditer(normalized_summary):
            candidate = match.group(0)
            if candidate not in normalized_original:
                ungrounded.append(candidate)
    return ungrounded
