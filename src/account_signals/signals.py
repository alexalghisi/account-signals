from __future__ import annotations

from collections.abc import Iterable
from datetime import date

from account_signals.models import Event, Intent, Reason

EVENT_WEIGHTS: dict[str, float] = {
    "pricing_page_visit": 12,
    "docs_signup": 18,
    "webinar_attended": 6,
    "job_post_billing": 15,
    "trial_started": 25,
}

INTENT_WEIGHTS: dict[Intent, float] = {
    Intent.EVALUATING_COMPETITOR: 30,
    Intent.EXPANSION: 25,
    Intent.PRICING_CONCERN: 10,
    Intent.CHURN_RISK: -20,
    Intent.NONE: 0,
}

HALF_LIFE_DAYS = 14


def decay(occurred_on: date, today: date) -> float:
    age = max((today - occurred_on).days, 0)
    return float(0.5 ** (age / HALF_LIFE_DAYS))


def event_signals(events: Iterable[Event], today: date) -> tuple[float, list[Reason]]:
    reasons: list[Reason] = []
    for event in events:
        weight = EVENT_WEIGHTS.get(event.kind)
        if weight is None:
            continue
        points = round(weight * decay(event.occurred_on, today), 2)
        age = (today - event.occurred_on).days
        reasons.append(Reason(event.kind, points, f"{event.kind.replace('_', ' ')} {age} days ago"))
    return sum(reason.points for reason in reasons), reasons


def note_signals(
    classified: Iterable[tuple[date, Intent]], today: date
) -> tuple[float, list[Reason]]:
    reasons = [
        Reason(
            f"note:{intent.value}",
            round(INTENT_WEIGHTS[intent] * decay(written, today), 2),
            f"CRM note suggests {intent.value.replace('_', ' ')}",
        )
        for written, intent in classified
        if intent is not Intent.NONE
    ]
    return sum(reason.points for reason in reasons), reasons
