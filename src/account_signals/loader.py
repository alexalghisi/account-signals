from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from account_signals.models import Account, Event, Note
from account_signals.store import Store


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_directory(store: Store, directory: Path) -> None:
    store.upsert_accounts(
        [
            Account(
                account_id=row["account_id"],
                name=row["name"],
                industry=row["industry"],
                country=row["country"],
                employees=int(row["employees"]),
                annual_revenue_usd=int(row["annual_revenue_usd"]),
                sells_software=row["sells_software"].lower() == "true",
            )
            for row in _rows(directory / "accounts.csv")
        ]
    )
    store.replace_events(
        [
            Event(row["account_id"], row["kind"], date.fromisoformat(row["occurred_on"]))
            for row in _rows(directory / "events.csv")
        ]
    )
    store.upsert_notes(
        [
            Note(
                row["note_id"],
                row["account_id"],
                date.fromisoformat(row["written_on"]),
                row["text"],
            )
            for row in _rows(directory / "notes.csv")
        ]
    )
    store.db.commit()
