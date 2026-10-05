from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest

from account_signals.store import Store, connect

TODAY = date(2026, 10, 5)
DATA = Path(__file__).resolve().parents[1] / "data"


@pytest.fixture
def connection() -> Iterator[sqlite3.Connection]:
    db = connect(":memory:")
    yield db
    db.close()


@pytest.fixture
def store(connection: sqlite3.Connection) -> Store:
    return Store(connection)
