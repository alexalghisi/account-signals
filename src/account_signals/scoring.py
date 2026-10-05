from __future__ import annotations

from account_signals.models import Reason, Score, Tier

TIER_A = 70.0
TIER_B = 40.0


def combine(
    account_id: str,
    fit: float,
    fit_reasons: list[Reason],
    intent: float,
    intent_reasons: list[Reason],
) -> Score:
    bounded_intent = max(min(intent, 100.0), -100.0)
    priority = round(fit * 0.6 + bounded_intent * 0.4, 2)
    tier = Tier.A if priority >= TIER_A else Tier.B if priority >= TIER_B else Tier.C
    reasons = sorted([*fit_reasons, *intent_reasons], key=lambda reason: -abs(reason.points))
    return Score(account_id, round(fit, 2), round(bounded_intent, 2), priority, tier, reasons)
