from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import date
from importlib import resources

from account_signals.models import Account, Event, Intent, Note, Reason, Score, Tier
from account_signals.notes import Classification


def connect(path: str) -> sqlite3.Connection:
    connection = sqlite3.connect(path, check_same_thread=False)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(resources.files("account_signals").joinpath("schema.sql").read_text())
    return connection


class Store:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.db = connection

    def upsert_accounts(self, accounts: list[Account]) -> None:
        self.db.executemany(
            "INSERT OR REPLACE INTO accounts VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    a.account_id,
                    a.name,
                    a.industry,
                    a.country,
                    a.employees,
                    a.annual_revenue_usd,
                    int(a.sells_software),
                )
                for a in accounts
            ],
        )

    def replace_events(self, events: list[Event]) -> None:
        self.db.execute("DELETE FROM events")
        self.db.executemany(
            "INSERT INTO events VALUES (?, ?, ?)",
            [(e.account_id, e.kind, e.occurred_on.isoformat()) for e in events],
        )

    def upsert_notes(self, notes: list[Note]) -> None:
        self.db.executemany(
            "INSERT OR REPLACE INTO notes VALUES (?, ?, ?, ?)",
            [(n.note_id, n.account_id, n.written_on.isoformat(), n.text) for n in notes],
        )

    def accounts(self) -> list[Account]:
        rows = self.db.execute("SELECT * FROM accounts ORDER BY account_id").fetchall()
        return [Account(r[0], r[1], r[2], r[3], r[4], r[5], bool(r[6])) for r in rows]

    def events_for(self, account_id: str) -> list[Event]:
        rows = self.db.execute(
            "SELECT account_id, kind, occurred_on FROM events WHERE account_id = ?", (account_id,)
        ).fetchall()
        return [Event(r[0], r[1], date.fromisoformat(r[2])) for r in rows]

    def unlabelled_notes(self) -> list[Note]:
        rows = self.db.execute(
            "SELECT n.note_id, n.account_id, n.written_on, n.text FROM notes n"
            " LEFT JOIN note_labels l ON l.note_id = n.note_id WHERE l.note_id IS NULL"
        ).fetchall()
        return [Note(r[0], r[1], date.fromisoformat(r[2]), r[3]) for r in rows]

    def labelled_intents(self, account_id: str) -> list[tuple[date, Intent]]:
        rows = self.db.execute(
            "SELECT n.written_on, l.intent FROM notes n JOIN note_labels l USING (note_id)"
            " WHERE n.account_id = ?",
            (account_id,),
        ).fetchall()
        return [(date.fromisoformat(r[0]), Intent(r[1])) for r in rows]

    def save_classification(self, result: Classification, purpose: str) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO note_labels VALUES (?, ?, ?, ?, ?)",
            (
                result.note.note_id,
                result.intent.value,
                result.evidence,
                result.completion.model,
                int(result.rejected_output),
            ),
        )
        completion = result.completion
        self.db.execute(
            "INSERT INTO llm_calls (model, purpose, input_tokens, output_tokens, latency_ms,"
            " cost_usd, cached) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                completion.model,
                purpose,
                completion.input_tokens,
                completion.output_tokens,
                completion.latency_ms,
                result.cost_usd,
                int(completion.cached),
            ),
        )

    def save_score(self, score: Score, scored_on: date) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO scores VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                score.account_id,
                score.fit,
                score.intent,
                score.priority,
                score.tier.value,
                json.dumps([asdict(reason) for reason in score.reasons]),
                scored_on.isoformat(),
            ),
        )

    def scores(self, tier: Tier | None = None) -> list[tuple[Account, Score]]:
        query = (
            "SELECT a.*, s.fit, s.intent, s.priority, s.tier, s.reasons FROM scores s"
            " JOIN accounts a USING (account_id)"
        )
        params: tuple[str, ...] = ()
        if tier is not None:
            query += " WHERE s.tier = ?"
            params = (tier.value,)
        rows = self.db.execute(query + " ORDER BY s.priority DESC", params).fetchall()
        return [
            (
                Account(r[0], r[1], r[2], r[3], r[4], r[5], bool(r[6])),
                Score(
                    r[0],
                    r[7],
                    r[8],
                    r[9],
                    Tier(r[10]),
                    [Reason(**reason) for reason in json.loads(r[11])],
                ),
            )
            for r in rows
        ]

    def llm_usage(self) -> dict[str, float]:
        row = self.db.execute(
            "SELECT COUNT(*), COALESCE(SUM(cost_usd), 0), COALESCE(AVG(latency_ms), 0),"
            " COALESCE(SUM(cached), 0), COALESCE(SUM(input_tokens + output_tokens), 0)"
            " FROM llm_calls"
        ).fetchone()
        calls = row[0] or 0
        return {
            "calls": calls,
            "cost_usd": round(row[1], 6),
            "avg_latency_ms": round(row[2], 2),
            "cache_hit_rate": round(row[3] / calls, 3) if calls else 0.0,
            "tokens": row[4],
        }
