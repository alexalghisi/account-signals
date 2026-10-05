from __future__ import annotations

import json
import sqlite3
import sys
from collections import Counter
from datetime import date
from pathlib import Path

from account_signals.models import Intent, Note
from account_signals.store import connect
from account_signals.wiring import build_classifier

THRESHOLD = float(sys.argv[1]) if len(sys.argv) > 1 else 0.0


def main() -> int:
    connection: sqlite3.Connection = connect(":memory:")
    classifier = build_classifier(connection)
    cases = [json.loads(line) for line in Path(__file__).with_name("labelled_notes.jsonl").open()]
    confusion: Counter[tuple[str, str]] = Counter()
    latencies: list[float] = []
    cost = 0.0
    rejected = 0
    cache_hits = 0
    for index, case in enumerate(cases):
        note = Note(f"eval_{index}", "eval", date(2026, 10, 1), case["text"])
        for _ in range(2):
            result = classifier.classify(note)
            cache_hits += int(result.completion.cached)
            if not result.completion.cached:
                latencies.append(result.completion.latency_ms)
                cost += result.cost_usd
        rejected += int(result.rejected_output)
        confusion[(case["intent"], result.intent.value)] += 1

    correct = sum(count for (gold, predicted), count in confusion.items() if gold == predicted)
    accuracy = correct / len(cases)
    print(f"model: {result.completion.model}")
    print(f"{'intent':<24}{'precision':>10}{'recall':>8}")
    for intent in Intent:
        tp = confusion[(intent.value, intent.value)]
        predicted = sum(c for (_, p), c in confusion.items() if p == intent.value)
        actual = sum(c for (g, _), c in confusion.items() if g == intent.value)
        precision = tp / predicted if predicted else 0.0
        recall = tp / actual if actual else 0.0
        print(f"{intent.value:<24}{precision:>10.2f}{recall:>8.2f}")
    misses = [(g, p) for (g, p), c in confusion.items() if g != p for _ in range(c)]
    for gold, predicted in misses:
        print(f"  miss: expected {gold}, got {predicted}")
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
    print(
        f"\naccuracy {accuracy:.0%} · rejected outputs {rejected}"
        f" · avg latency {avg_latency:.1f} ms · cost ${cost:.4f}"
        f" · cache hits {cache_hits}/{2 * len(cases)}"
    )
    return 0 if accuracy >= THRESHOLD else 1


if __name__ == "__main__":
    raise SystemExit(main())
