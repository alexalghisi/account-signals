from __future__ import annotations

from collections.abc import Callable
from datetime import date

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from account_signals.models import Tier
from account_signals.notes import NoteClassifier
from account_signals.pipeline import refresh
from account_signals.report import render_report
from account_signals.store import Store


class ReasonOut(BaseModel):
    factor: str
    points: float
    detail: str


class AccountScoreOut(BaseModel):
    account_id: str
    name: str
    tier: Tier
    priority: float
    fit: float
    intent: float
    reasons: list[ReasonOut]


def create_app(store: Store, classifier: NoteClassifier, today: Callable[[], date]) -> FastAPI:
    app = FastAPI(title="Account signals", version="0.1.0")

    def scored(tier: Tier | None = None) -> list[AccountScoreOut]:
        return [
            AccountScoreOut(
                account_id=account.account_id,
                name=account.name,
                tier=score.tier,
                priority=score.priority,
                fit=score.fit,
                intent=score.intent,
                reasons=[ReasonOut(**vars(reason)) for reason in score.reasons],
            )
            for account, score in store.scores(tier)
        ]

    @app.post("/refresh")
    def run_refresh() -> dict[str, int]:
        summary = refresh(store, classifier, today())
        return vars(summary)

    @app.get("/accounts", response_model=list[AccountScoreOut])
    def list_accounts(tier: Tier | None = None) -> list[AccountScoreOut]:
        return scored(tier)

    @app.get("/accounts/{account_id}", response_model=AccountScoreOut)
    def get_account(account_id: str) -> AccountScoreOut:
        match = next((row for row in scored() if row.account_id == account_id), None)
        if match is None:
            raise HTTPException(status_code=404, detail=f"No score for {account_id}")
        return match

    @app.get("/usage")
    def usage() -> dict[str, float]:
        return store.llm_usage()

    @app.get("/report", response_class=HTMLResponse)
    def report() -> str:
        return render_report(store.scores(), store.llm_usage())

    return app
