from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from account_signals.icp import FIT_FACTORS
from account_signals.loader import load_directory
from account_signals.pipeline import refresh
from account_signals.store import Store, connect
from account_signals.wiring import build_classifier


def main() -> None:
    parser = argparse.ArgumentParser(description="Score accounts from ICP fit and buying signals")
    parser.add_argument("--db", default="signals.db")
    parser.add_argument("--data", type=Path, default=Path("data"))
    parser.add_argument("--today", type=date.fromisoformat, default=date.today())
    args = parser.parse_args()

    connection = connect(args.db)
    store = Store(connection)
    load_directory(store, args.data)
    summary = refresh(store, build_classifier(connection), args.today)
    print(f"classified {summary.notes_classified} notes, scored {summary.accounts_scored} accounts")
    for account, score in store.scores():
        signal = next((r for r in score.reasons if r.factor not in FIT_FACTORS), None)
        top = signal.detail if signal else "no recent buying signals"
        print(f"{score.tier.value}  {score.priority:6.1f}  {account.name:<28} {top}")
    usage = store.llm_usage()
    print(
        f"\nLLM calls {usage['calls']:.0f} · ${usage['cost_usd']:.4f}"
        f" · {usage['cache_hit_rate']:.0%} cache hits"
    )
