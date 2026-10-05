from __future__ import annotations

import os
import sqlite3

from account_signals.llm import (
    CachedModel,
    KeywordModel,
    LanguageModel,
    ModelPrice,
    ModelRouter,
    OpenAIChatModel,
    Route,
)
from account_signals.notes import NoteClassifier

LONG_NOTE_CHARS = 600


def build_classifier(connection: sqlite3.Connection) -> NoteClassifier:
    api_key = os.environ.get("OPENAI_API_KEY")
    small: LanguageModel
    large: LanguageModel
    if api_key:
        small = OpenAIChatModel(os.environ.get("SIGNALS_SMALL_MODEL", "gpt-4o-mini"), api_key)
        large = OpenAIChatModel(os.environ.get("SIGNALS_LARGE_MODEL", "gpt-4o"), api_key)
        small_price, large_price = ModelPrice(0.15, 0.60), ModelPrice(2.50, 10.00)
    else:
        small = large = KeywordModel()
        small_price = large_price = ModelPrice(0, 0)
    router = ModelRouter(
        small=Route(CachedModel(small, connection), small_price),
        large=Route(CachedModel(large, connection), large_price),
        needs_large=lambda text: len(text) > LONG_NOTE_CHARS,
    )
    return NoteClassifier(router)
