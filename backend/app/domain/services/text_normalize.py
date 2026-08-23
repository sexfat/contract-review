from __future__ import annotations

import unicodedata


def normalize(text: str) -> str:
    """Full-width digits/punctuation -> half-width, so e.g. "１００元"
    matches "100元". Shared by summary_guard and risk_rule_matcher."""
    return unicodedata.normalize("NFKC", text)
