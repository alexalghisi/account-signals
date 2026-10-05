import json
import sqlite3
from datetime import date

import httpx
import pytest

from account_signals.llm import (
    CachedModel,
    Completion,
    KeywordModel,
    ModelPrice,
    ModelRouter,
    OpenAIChatModel,
    Route,
)
from account_signals.models import Intent, Note
from account_signals.notes import NoteClassifier

NOTE = Note("n1", "acc", date(2026, 10, 1), "They are comparing us with Chargebee this month.")


class FixedModel:
    def __init__(self, text: str, name: str = "fixed") -> None:
        self.name = name
        self.text = text
        self.calls = 0

    def complete(self, system: str, user: str) -> Completion:
        self.calls += 1
        return Completion(self.text, self.name, 1_000, 100, 12.5)


PRICE = ModelPrice(1.0, 2.0)


def classifier_for(model: FixedModel) -> NoteClassifier:
    route = Route(model, PRICE)
    return NoteClassifier(ModelRouter(route, route, needs_large=lambda _: False))


def test_accepts_valid_label_with_verbatim_evidence() -> None:
    model = FixedModel(json.dumps({"intent": "evaluating_competitor", "evidence": "comparing us"}))
    result = classifier_for(model).classify(NOTE)
    assert result.intent is Intent.EVALUATING_COMPETITOR
    assert not result.rejected_output
    assert result.cost_usd == pytest.approx((1_000 * 1.0 + 100 * 2.0) / 1_000_000)


@pytest.mark.parametrize(
    "text",
    [
        "not json",
        json.dumps({"intent": "buying_now", "evidence": ""}),
        json.dumps({"label": "expansion"}),
        json.dumps({"intent": "expansion", "evidence": "they want 200 more seats"}),
    ],
)
def test_rejects_malformed_or_hallucinated_output(text: str) -> None:
    result = classifier_for(FixedModel(text)).classify(NOTE)
    assert result.intent is Intent.NONE
    assert result.rejected_output


def test_cache_serves_repeated_prompts_without_cost(connection: sqlite3.Connection) -> None:
    inner = FixedModel(json.dumps({"intent": "none", "evidence": ""}))
    cached = CachedModel(inner, connection)
    first = cached.complete("system", "user")
    second = cached.complete("system", "user")
    assert inner.calls == 1
    assert second.cached
    assert ModelPrice(5, 5).cost(second) == 0
    assert (second.text, second.input_tokens) == (first.text, first.input_tokens)


def test_router_sends_long_notes_to_the_large_model() -> None:
    small = Route(FixedModel("{}", "small"), ModelPrice(0, 0))
    large = Route(FixedModel("{}", "large"), ModelPrice(0, 0))
    router = ModelRouter(small, large, needs_large=lambda text: len(text) > 10)
    assert router.route("short").model.name == "small"
    assert router.route("a much longer note").model.name == "large"


def test_keyword_baseline_returns_parseable_labels() -> None:
    completion = KeywordModel().complete("", "We will not renew next year")
    assert json.loads(completion.text)["intent"] == "churn_risk"


def test_openai_adapter_requests_json_and_reports_usage() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        seen["auth"] = request.headers["Authorization"]
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": '{"intent": "none", "evidence": ""}'}}],
                "usage": {"prompt_tokens": 50, "completion_tokens": 9},
            },
        )

    model = OpenAIChatModel("gpt-4o-mini", "sk-test", transport=httpx.MockTransport(handler))
    completion = model.complete("system prompt", "note text")

    assert seen["response_format"] == {"type": "json_object"}
    assert seen["temperature"] == 0
    assert seen["auth"] == "Bearer sk-test"
    assert (completion.input_tokens, completion.output_tokens) == (50, 9)
