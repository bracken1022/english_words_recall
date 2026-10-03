"""Client for the local Ollama chat API used for grammar/naturalness
correction (contracts/ollama-correction-contract.md; FR-007, FR-008, FR-009,
FR-010). Spec 010 splits the single review call into two roles — see
contracts/ollama-correction-contract-delta.md: a Judge call (grammar,
target-expression usage, naturalness) and, only when the Judge found a
problem, a Teacher call (explanation + rewrite).

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

_JUDGE_SYSTEM_PROMPT = (
    "You are an English grammar and naturalness judge for a language "
    "learner. Respond only with the requested JSON object."
)

_JUDGE_RESPONSE_FORMAT = {
    "type": "object",
    "properties": {
        "uses_expression": {"type": "boolean"},
        "grammatically_correct": {"type": "boolean"},
        "natural": {"type": "boolean"},
    },
    "required": ["uses_expression", "grammatically_correct", "natural"],
}

_JUDGE_REQUIRED_FIELDS = ("uses_expression", "grammatically_correct", "natural")

_TEACHER_SYSTEM_PROMPT = (
    "You are an English writing teacher helping a language learner fix a "
    "mistake in their sentence. Preserve the learner's intended meaning "
    "and the target expression. Make only the changes needed for grammar "
    "and naturalness; do not replace an action or idea with a different "
    "one. Respond only with the requested JSON object."
)

_TEACHER_RESPONSE_FORMAT = {
    "type": "object",
    "properties": {
        "corrected": {"type": "string"},
        "explanation": {"type": "string"},
    },
    "required": ["corrected", "explanation"],
}

_TEACHER_REQUIRED_FIELDS = ("corrected", "explanation")


@dataclass
class CorrectionResult:
    available: bool
    uses_expression: bool | None
    needs_correction: bool | None
    corrected: str | None
    explanation: str | None


@dataclass
class _JudgeVerdict:
    uses_expression: bool
    grammatically_correct: bool
    natural: bool


def _unavailable() -> CorrectionResult:
    return CorrectionResult(
        available=False,
        uses_expression=None,
        needs_correction=None,
        corrected=None,
        explanation=None,
    )


def _post_chat(base_url: str, payload: dict, timeout: float) -> tuple[str | None, str | None]:
    """POST *payload* to the local chat API and return (content, failure).
    On success failure is None; otherwise content is None and failure is
    "unavailable" (can't connect, or 404 — model not pulled), "timeout",
    "bad_status", "bad_body" or "error". Spec 018's enrichment needs this
    distinction; sentence review uses _post_json, which collapses it."""
    try:
        response = requests.post(f"{base_url}/api/chat", json=payload, timeout=timeout)
    except requests.ConnectionError:
        return None, "unavailable"
    except requests.Timeout:
        return None, "timeout"
    except requests.RequestException:
        return None, "error"
    except ConnectionError:
        return None, "unavailable"

    if response.status_code == 404:
        return None, "unavailable"
    if response.status_code != 200:
        return None, "bad_status"

    try:
        content = response.json()["message"]["content"]
    except (KeyError, TypeError, ValueError):
        return None, "bad_body"
    return content, None


def _post_json(base_url: str, payload: dict, timeout: float) -> str | None:
    """Shared request plumbing for both roles: POST *payload*, return the
    reply's message content string, or None on any failure (connection
    error, non-200 status, or a response missing that field) — the caller
    treats that identically to an unavailable LLM (FR-010)."""
    content, _failure = _post_chat(base_url, payload, timeout)
    return content


def _parse_object_reply(
    content: str,
    required_fields: tuple[str, ...],
    bool_fields: tuple[str, ...] = (),
    str_fields: tuple[str, ...] = (),
) -> dict | None:
    """Generic structured-reply parser shared by both roles: valid JSON
    object, all required_fields present, bool_fields/str_fields correctly
    typed. Returns the parsed dict, or None if anything doesn't hold."""
    try:
        data = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return None

    if not isinstance(data, dict):
        return None

    if any(field not in data for field in required_fields):
        return None

    for field in bool_fields:
        if not isinstance(data[field], bool):
            return None
    for field in str_fields:
        if not isinstance(data[field], str):
            return None

    return data


def _request_judge(
    target_expression: str, sentence: str, base_url: str, model: str, timeout: float
) -> _JudgeVerdict | None:
    payload = {
        "model": model,
        "stream": False,
        "think": False,
        "format": _JUDGE_RESPONSE_FORMAT,
        "messages": [
            {"role": "system", "content": _JUDGE_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f'Target expression: "{target_expression}". '
                    f'Learner\'s sentence: "{sentence}". '
                    "Does the sentence use the target expression? Is it "
                    "grammatically correct? Does it sound natural to a "
                    "native speaker?"
                ),
            },
        ],
    }

    content = _post_json(base_url, payload, timeout)
    if content is None:
        return None

    data = _parse_object_reply(content, _JUDGE_REQUIRED_FIELDS, bool_fields=_JUDGE_REQUIRED_FIELDS)
    if data is None:
        return None

    return _JudgeVerdict(
        uses_expression=data["uses_expression"],
        grammatically_correct=data["grammatically_correct"],
        natural=data["natural"],
    )


def _request_teacher(
    target_expression: str, sentence: str, base_url: str, model: str, timeout: float
) -> tuple[str, str] | None:
    payload = {
        "model": model,
        "stream": False,
        "think": False,
        "format": _TEACHER_RESPONSE_FORMAT,
        "messages": [
            {"role": "system", "content": _TEACHER_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f'Target expression: "{target_expression}". '
                    f'Learner\'s sentence: "{sentence}". '
                    "This sentence has a grammar or naturalness problem. "
                    "Provide a corrected, natural version and a "
                    "one-to-two sentence explanation of the mistake."
                ),
            },
        ],
    }

    content = _post_json(base_url, payload, timeout)
    if content is None:
        return None

    data = _parse_object_reply(content, _TEACHER_REQUIRED_FIELDS, str_fields=_TEACHER_REQUIRED_FIELDS)
    if data is None:
        return None

    return data["corrected"], data["explanation"]


def request_correction(
    target_expression: str,
    sentence: str,
    base_url: str,
    model: str = DEFAULT_MODEL,
    timeout: float = 30.0,
) -> CorrectionResult:
    """Send *sentence* for grammar/naturalness review against
    *target_expression*: a Judge call first, then — only if it found a
    grammar or naturalness problem — a Teacher call for the explanation
    and rewrite. Any failure at either step (connection error, non-200
    status, or a reply that fails to parse/validate) is reported as
    `available=False` rather than raised; a Teacher-call failure discards
    the Judge's already-successful verdict rather than returning a partial
    result (spec 010 FR-005)."""
    verdict = _request_judge(target_expression, sentence, base_url, model, timeout)
    if verdict is None:
        return _unavailable()

    needs_correction = not (verdict.grammatically_correct and verdict.natural)
    if not needs_correction:
        return CorrectionResult(
            available=True,
            uses_expression=verdict.uses_expression,
            needs_correction=False,
            corrected=None,
            explanation=None,
        )

    teacher_reply = _request_teacher(target_expression, sentence, base_url, model, timeout)
    if teacher_reply is None:
        return _unavailable()

    corrected, explanation = teacher_reply
    return CorrectionResult(
        available=True,
        uses_expression=verdict.uses_expression,
        needs_correction=True,
        corrected=corrected,
        explanation=explanation,
    )
