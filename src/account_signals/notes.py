from __future__ import annotations

import json
from dataclasses import dataclass

from account_signals.llm import Completion, ModelRouter
from account_signals.models import Intent, Note

SYSTEM_PROMPT = """You label CRM notes written by account executives.
Return JSON: {"intent": one of ["evaluating_competitor", "pricing_concern", "expansion",
"churn_risk", "none"], "evidence": a short quote copied verbatim from the note}.
Use "none" when the note does not clearly support another label."""


@dataclass(frozen=True)
class Classification:
    note: Note
    intent: Intent
    evidence: str
    completion: Completion
    cost_usd: float
    rejected_output: bool


def _parse(completion: Completion, note: Note) -> tuple[Intent, str, bool]:
    try:
        payload = json.loads(completion.text)
        intent = Intent(payload["intent"])
        evidence = str(payload.get("evidence", ""))
    except (ValueError, KeyError, TypeError):
        return Intent.NONE, "", True
    if evidence and evidence.lower() not in note.text.lower():
        return Intent.NONE, "", True
    return intent, evidence, False


class NoteClassifier:
    def __init__(self, router: ModelRouter) -> None:
        self._router = router

    def classify(self, note: Note) -> Classification:
        route = self._router.route(note.text)
        completion = route.model.complete(SYSTEM_PROMPT, note.text)
        intent, evidence, rejected = _parse(completion, note)
        return Classification(
            note=note,
            intent=intent,
            evidence=evidence,
            completion=completion,
            cost_usd=route.price.cost(completion),
            rejected_output=rejected,
        )
