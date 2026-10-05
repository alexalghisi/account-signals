from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

import httpx


@dataclass(frozen=True)
class Completion:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    cached: bool = False


@dataclass(frozen=True)
class ModelPrice:
    input_per_million: float
    output_per_million: float

    def cost(self, completion: Completion) -> float:
        if completion.cached:
            return 0.0
        return (
            completion.input_tokens * self.input_per_million
            + completion.output_tokens * self.output_per_million
        ) / 1_000_000


class LanguageModel(Protocol):
    name: str

    def complete(self, system: str, user: str) -> Completion: ...


class OpenAIChatModel:
    def __init__(
        self,
        name: str,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.name = name
        self._client = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30,
            transport=transport,
        )

    def complete(self, system: str, user: str) -> Completion:
        started = time.perf_counter()
        response = self._client.post(
            "/chat/completions",
            json={
                "model": self.name,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
        )
        response.raise_for_status()
        body = response.json()
        return Completion(
            text=body["choices"][0]["message"]["content"],
            model=self.name,
            input_tokens=body["usage"]["prompt_tokens"],
            output_tokens=body["usage"]["completion_tokens"],
            latency_ms=(time.perf_counter() - started) * 1000,
        )


class KeywordModel:
    name = "keyword-baseline"

    _RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
        ("churn_risk", re.compile(r"\b(cancel|churn|not renew|leaving|downgrade)", re.I)),
        (
            "evaluating_competitor",
            re.compile(r"\b(stripe|chargebee|recurly|competitor|alternatives?|comparing)\b", re.I),
        ),
        (
            "expansion",
            re.compile(r"\b(expand|new region|more seats|launching in|additional product)", re.I),
        ),
        ("pricing_concern", re.compile(r"\b(too expensive|price|pricing|fees?|discount)\b", re.I)),
    )

    def complete(self, system: str, user: str) -> Completion:
        started = time.perf_counter()
        intent = next((name for name, pattern in self._RULES if pattern.search(user)), "none")
        text = json.dumps({"intent": intent, "evidence": ""})
        return Completion(
            text, self.name, len(user) // 4, 12, (time.perf_counter() - started) * 1000
        )


class CachedModel:
    def __init__(self, inner: LanguageModel, connection: sqlite3.Connection) -> None:
        self.name = inner.name
        self._inner = inner
        self._db = connection

    def complete(self, system: str, user: str) -> Completion:
        key = hashlib.sha256(f"{self.name}\n{system}\n{user}".encode()).hexdigest()
        row = self._db.execute(
            "SELECT text, input_tokens, output_tokens FROM llm_cache WHERE cache_key = ?", (key,)
        ).fetchone()
        if row:
            return Completion(row[0], self.name, row[1], row[2], 0.0, cached=True)
        completion = self._inner.complete(system, user)
        self._db.execute(
            "INSERT OR REPLACE INTO llm_cache (cache_key, model, text, input_tokens, output_tokens)"
            " VALUES (?, ?, ?, ?, ?)",
            (key, self.name, completion.text, completion.input_tokens, completion.output_tokens),
        )
        return completion


@dataclass(frozen=True)
class Route:
    model: LanguageModel
    price: ModelPrice


class ModelRouter:
    def __init__(self, small: Route, large: Route, needs_large: Callable[[str], bool]) -> None:
        self._small = small
        self._large = large
        self._needs_large = needs_large

    def route(self, user: str) -> Route:
        return self._large if self._needs_large(user) else self._small
