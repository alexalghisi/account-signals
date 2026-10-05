from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from account_signals.icp import DEFAULT_ICP, IdealCustomerProfile, fit_score
from account_signals.notes import NoteClassifier
from account_signals.scoring import combine
from account_signals.signals import event_signals, note_signals
from account_signals.store import Store


@dataclass(frozen=True)
class RefreshSummary:
    notes_classified: int
    rejected_outputs: int
    accounts_scored: int


def refresh(
    store: Store,
    classifier: NoteClassifier,
    today: date,
    icp: IdealCustomerProfile = DEFAULT_ICP,
) -> RefreshSummary:
    rejected = 0
    notes = store.unlabelled_notes()
    for note in notes:
        result = classifier.classify(note)
        rejected += int(result.rejected_output)
        store.save_classification(result, purpose="note_intent")
    accounts = store.accounts()
    for account in accounts:
        fit, fit_reasons = fit_score(account, icp)
        events, event_reasons = event_signals(store.events_for(account.account_id), today)
        intents, intent_reasons = note_signals(store.labelled_intents(account.account_id), today)
        store.save_score(
            combine(
                account.account_id,
                fit,
                fit_reasons,
                events + intents,
                event_reasons + intent_reasons,
            ),
            today,
        )
    store.db.commit()
    return RefreshSummary(len(notes), rejected, len(accounts))
