from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from account_signals.api import create_app
from account_signals.loader import load_directory
from account_signals.store import Store, connect
from account_signals.wiring import build_classifier

_connection = connect(os.environ.get("SIGNALS_DB", "signals.db"))
_store = Store(_connection)
if data_dir := os.environ.get("SIGNALS_SEED_DIR"):
    load_directory(_store, Path(data_dir))
app = create_app(_store, build_classifier(_connection), date.today)
