from __future__ import annotations

from html import escape
from importlib import resources

from account_signals.models import Account, Score

_CSS = resources.files("account_signals").joinpath("report.css").read_text()


def _reasons(score: Score) -> str:
    items = (
        f"<li><b>{reason.points:+.0f}</b> {escape(reason.detail)}</li>"
        for reason in score.reasons[:4]
    )
    return f"<ul>{''.join(items)}</ul>"


def _card(account: Account, score: Score) -> str:
    tier = score.tier.value
    meta = (
        f"{escape(account.industry)} · {escape(account.country)} · {account.employees} people"
        f" · fit {score.fit:.0f} · intent {score.intent:.0f}"
    )
    return (
        f'<article class="card"><header><span class="tier tier-{tier}">{tier}</span>'
        f"<h2>{escape(account.name)}</h2>"
        f'<span class="priority">{score.priority:.0f}</span></header>'
        f'<p class="meta">{meta}</p>{_reasons(score)}</article>'
    )


def render_report(rows: list[tuple[Account, Score]], usage: dict[str, float]) -> str:
    stats = (
        f"{usage['calls']:.0f} LLM calls · ${usage['cost_usd']:.4f}"
        f" · {usage['avg_latency_ms']:.0f} ms avg · {usage['cache_hit_rate']:.0%} cache hits"
    )
    cards = "".join(_card(account, score) for account, score in rows)
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>Account priorities</title><style>{_CSS}</style></head><body>"
        f'<div class="top"><h1>Account priorities</h1><span class="stats">{stats}</span></div>'
        f"<main>{cards}</main></body></html>"
    )
