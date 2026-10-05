from datetime import date

from fastapi.testclient import TestClient

from account_signals.api import create_app
from account_signals.loader import load_directory
from account_signals.models import Tier
from account_signals.pipeline import refresh
from account_signals.store import Store
from account_signals.wiring import build_classifier

from .conftest import DATA, TODAY


def loaded(store: Store) -> Store:
    load_directory(store, DATA)
    return store


def test_refresh_classifies_notes_once_and_ranks_accounts(store: Store) -> None:
    classifier = build_classifier(loaded(store).db)

    first = refresh(store, classifier, TODAY)
    second = refresh(store, classifier, TODAY)

    assert (first.notes_classified, first.accounts_scored) == (6, 8)
    assert second.notes_classified == 0
    ranking = [account.name for account, _ in store.scores()]
    assert ranking[0] == "Northwind Analytics"
    assert {account.name for account, _ in store.scores(Tier.A)} == {
        "Northwind Analytics",
        "Lumen Dev Tools",
    }
    assert store.llm_usage()["calls"] == 6


def test_scores_decay_as_signals_age(store: Store) -> None:
    classifier = build_classifier(loaded(store).db)
    refresh(store, classifier, TODAY)
    fresh = dict((a.account_id, s.priority) for a, s in store.scores())
    refresh(store, classifier, date(2026, 12, 31))
    stale = dict((a.account_id, s.priority) for a, s in store.scores())
    assert stale["acc_001"] < fresh["acc_001"]


def test_api_exposes_ranked_accounts_report_and_usage(store: Store) -> None:
    app = create_app(loaded(store), build_classifier(store.db), lambda: TODAY)
    client = TestClient(app)

    assert client.post("/refresh").json() == {
        "notes_classified": 6,
        "rejected_outputs": 0,
        "accounts_scored": 8,
    }
    tier_a = client.get("/accounts", params={"tier": "A"}).json()
    assert [row["name"] for row in tier_a] == ["Northwind Analytics", "Lumen Dev Tools"]
    detail = client.get("/accounts/acc_001").json()
    assert any(reason["factor"] == "note:evaluating_competitor" for reason in detail["reasons"])
    assert client.get("/accounts/acc_999").status_code == 404
    assert "Northwind Analytics" in client.get("/report").text
    assert client.get("/usage").json()["calls"] == 6
