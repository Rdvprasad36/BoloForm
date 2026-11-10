"""Risk-adaptive confirmation policy.

Goal: ask fewer confirmations without letting wrong values through.
Thresholds are DEFAULTS. Tune them on the eval *dev* split only; report on the *test* split.
"""
from __future__ import annotations

from .forms import FieldDef
from .parsers import ParseResult

T_LOW = 0.30
T_HIGH = 0.60

MODES = ("digits", "explicit", "simple", "implicit")


def risk_score(field: FieldDef, parsed: ParseResult, confidence: float | None,
               snr_db: float | None, attempts: int) -> float:
    score = {"low": 0.0, "medium": 0.30, "critical": 0.60}[field.risk]
    score += (1.0 - confidence) * 0.50 if confidence is not None else 0.20   # unknown = mild penalty
    if snr_db is not None and snr_db < 15:
        score += 0.20
    if parsed.ambiguous:
        score += 0.20
    score += 0.15 * attempts
    return score


def decide_confirm_mode(field: FieldDef, parsed: ParseResult, confidence: float | None = None,
                        snr_db: float | None = None, attempts: int = 0,
                        policy: str = "adaptive") -> str:
    """Return one of: digits | explicit | simple | implicit."""
    if policy == "never":
        return "implicit"
    if field.risk == "critical" or policy == "always":
        return "digits" if field.type == "phone" else "explicit"
    s = risk_score(field, parsed, confidence, snr_db, attempts)
    if s >= T_HIGH:
        return "digits" if field.type == "phone" else "explicit"
    if s >= T_LOW:
        return "simple"
    return "implicit"
