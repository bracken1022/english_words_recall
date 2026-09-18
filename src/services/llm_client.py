"""Client for the local Ollama chat API used for grammar/naturalness
correction (contracts/ollama-correction-contract.md; FR-007, FR-008, FR-009,
FR-010).

Boundary rule: the CorrectionResult returned here is an opaque evaluation
payload for display/logging only. Nothing here, and nothing that consumes
it, may use it to influence session control flow (grading, item ordering,
progression) — see plan.md Constraints and research.md "Determinism of the
learning state machine."
"""

import json
from dataclasses import dataclass

import requests

DEFAULT_MODEL = "qwen3:14b"

_SYSTEM_PROMPT = (
    "You are an English grammar and naturalness checker for a language "
    "learner. Respond only with the requested JSON object."
)

_RESPONSE_FORMAT = {
    "type": "object",
    "properties": {
        "uses_expression": {"type": "boolean"},
        "needs_correction": {"type": "boolean"},
        "corrected": {"type": ["string", "null"]},
        "explanation": {"type": ["string", "null"]},
    },
    "required": ["uses_expression", "needs_correction", "corrected", "explanation"],
}

_REQUIRED_FIELDS = ("uses_expression", "needs_correction", "corrected", "explanation")


@dataclass
class CorrectionResult:
    available: bool
    uses_expression: bool | None
    needs_correction: bool | None
    corrected: str | None
    explanation: str | None


def _unavailable() -> CorrectionResult:
    return CorrectionResult(
        available=False,
        uses_expression=None,
        needs_correction=None,
        corrected=None,
        explanation=None,
    )


def _parse_reply(content: str) -> CorrectionResult | None:
    """Parse Ollama's structured-output JSON reply. Returns None if it isn't
    valid JSON, isn't an object, is missing a required key, or has a
    required key of the wrong type — the caller treats that identically to
    an unavailable LLM (FR-010)."""
    try:
        data = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return None

    if not isinstance(data, dict):
        return None

    if any(field not in data for field in _REQUIRED_FIELDS):
        return None

    uses_expression = data["uses_expression"]
    needs_correction = data["needs_correction"]
    corrected = data["corrected"]
    explanation = data["explanation"]

    if not isinstance(uses_expression, bool) or not isinstance(needs_correction, bool):
        return None
    if corrected is not None and not isinstance(corrected, str):
        return None
    if explanation is not None and not isinstance(explanation, str):
        return None

    return CorrectionResult(
        available=True,
        uses_expression=uses_expression,
        needs_correction=needs_correction,
        corrected=corrected if needs_correction else None,
        explanation=explanation if needs_correction else None,
    )


def request_correction(
    target_expression: str,
    sentence: str,
    base_url: str,
    model: str = DEFAULT_MODEL,
    timeout: float = 30.0,
) -> CorrectionResult:
    """Send *sentence* for grammar/naturalness review against
    *target_expression*, requesting Ollama's structured JSON output. Any
    failure (connection error, non-200 status, or a reply that fails to
    parse/validate against the schema) is reported as `available=False`
    rather than raised."""
    payload = {
        "model": model,
        "stream": False,
        "format": _RESPONSE_FORMAT,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f'Target expression: "{target_expression}". '
                    f'Learner\'s sentence: "{sentence}". '
                    "Does the sentence use the target expression? Is it "
                    "grammatically correct and natural? If not, provide a "
                    "corrected sentence and a one-to-two sentence "
                    "explanation; otherwise leave those two fields null."
                ),
            },
        ],
    }

    try:
        response = requests.post(f"{base_url}/api/chat", json=payload, timeout=timeout)
    except requests.RequestException:
        return _unavailable()
    except ConnectionError:
        return _unavailable()

    if response.status_code != 200:
        return _unavailable()

    try:
        content = response.json()["message"]["content"]
    except (KeyError, TypeError, ValueError):
        return _unavailable()

    parsed = _parse_reply(content)
    return parsed if parsed is not None else _unavailable()
