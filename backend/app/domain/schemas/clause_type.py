from __future__ import annotations

from enum import Enum


class ClauseType(str, Enum):
    SCOPE = "scope"
    ACCEPTANCE = "acceptance"
    PAYMENT = "payment"
    IP = "ip"
    WARRANTY = "warranty"
    LIABILITY = "liability"
    TERMINATION = "termination"
    PENALTY = "penalty"
    CONFIDENTIALITY = "confidentiality"
    OTHER = "other"
