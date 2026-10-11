"""Shared plumbing for the local Ollama chat API (`/api/chat`).

Spec 021 removed sentence review (the Judge/Teacher correction calls that
used to live here); what remains is the transport and reply parsing that
enrichment (spec 018/019) and example sentences (spec 021) build on.
"""

import json

import requests

DEFAULT_MODEL = "qwen3:14b"


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
