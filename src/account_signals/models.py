from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum


class Intent(StrEnum):
    EVALUATING_COMPETITOR = "evaluating_competitor"
    PRICING_CONCERN = "pricing_concern"
    EXPANSION = "expansion"
    CHURN_RISK = "churn_risk"
    NONE = "none"


class Tier(StrEnum):
    A = "A"
    B = "B"
    C = "C"


@dataclass(frozen=True)
class Account:
    account_id: str
    name: str
    industry: str
    country: str
    employees: int
    annual_revenue_usd: int
    sells_software: bool


@dataclass(frozen=True)
class Event:
    account_id: str
    kind: str
    occurred_on: date


@dataclass(frozen=True)
class Note:
    note_id: str
    account_id: str
    written_on: date
    text: str


@dataclass(frozen=True)
class Reason:
    factor: str
    points: float
    detail: str


@dataclass
class Score:
    account_id: str
    fit: float
    intent: float
    priority: float
    tier: Tier
    reasons: list[Reason] = field(default_factory=list)
