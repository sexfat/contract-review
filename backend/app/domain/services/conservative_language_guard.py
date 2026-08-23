from __future__ import annotations

# Initial static blocklist for DEVELOPMENT_SPEC.md §2 原則 6 (保守措辭):
# risk concern/suggestion text must never assert a legal conclusion.
# Extend this list as needed — no LLM call involved, safe to tune freely.
_BANNED_PHRASES = [
    "本條無效",
    "一定會賠償",
    "保證勝訴",
    "絕對",
    "必然",
    "毫無疑問",
]


def find_banned_phrase(text: str) -> str | None:
    """Returns the first banned assertive phrase found in `text`, or None if
    the text passes."""
    for phrase in _BANNED_PHRASES:
        if phrase in text:
            return phrase
    return None
