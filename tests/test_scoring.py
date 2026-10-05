from datetime import date

import pytest

from account_signals.icp import fit_score
from account_signals.models import Account, Event, Intent, Tier
from account_signals.scoring import combine
from account_signals.signals import decay, event_signals, note_signals

TODAY = date(2026, 10, 5)

IDEAL = Account("a", "Northwind", "SaaS", "GB", 140, 18_000_000, True)
POOR = Account("b", "Harbor", "Logistics", "BR", 5, 500_000, False)


def test_ideal_account_scores_full_fit_with_reasons() -> None:
    fit, reasons = fit_score(IDEAL)
    assert fit == 100
    assert {reason.factor for reason in reasons} == {
        "sells_software",
        "industry",
        "region",
        "revenue",
        "size",
    }


def test_account_outside_icp_scores_zero() -> None:
    assert fit_score(POOR) == (0, [])


@pytest.mark.parametrize(("age", "expected"), [(0, 1.0), (14, 0.5), (28, 0.25)])
def test_signals_halve_every_two_weeks(age: int, expected: float) -> None:
    assert decay(date.fromordinal(TODAY.toordinal() - age), TODAY) == pytest.approx(expected)


def test_future_dated_events_do_not_boost_scores() -> None:
    assert decay(date(2026, 12, 1), TODAY) == 1.0


def test_event_signals_ignore_unknown_events() -> None:
    events = [
        Event("a", "trial_started", TODAY),
        Event("a", "newsletter_open", TODAY),
    ]
    points, reasons = event_signals(events, TODAY)
    assert points == 25
    assert [reason.factor for reason in reasons] == ["trial_started"]


def test_churn_risk_notes_reduce_intent() -> None:
    points, reasons = note_signals([(TODAY, Intent.CHURN_RISK), (TODAY, Intent.NONE)], TODAY)
    assert points == -20
    assert len(reasons) == 1


@pytest.mark.parametrize(
    ("fit", "intent", "tier"),
    [(100, 50, Tier.A), (70, 10, Tier.B), (40, 0, Tier.C), (100, -100, Tier.C)],
)
def test_priority_tiers(fit: float, intent: float, tier: Tier) -> None:
    assert combine("a", fit, [], intent, []).tier is tier


def test_intent_is_capped_so_noise_cannot_dominate_fit() -> None:
    assert combine("a", 0, [], 500, []).priority == 40
