"""Qwen via its OpenAI-compatible chat-completions API (backend only).

Three parts that change independently:
- QwenConfig: the key, endpoint and model, read from the environment
  (DASHSCOPE_API_KEY, QWEN_BASE_URL, QWEN_MODEL);
- complete_json(): the transport. One POST to {base_url}/chat/completions
  with thinking off, temperature 0, a JSON-object reply and a 45 s timeout;
- the task: its system prompt, user text and a validate() function that
  turns the parsed JSON into a typed result or raises ValueError (see
  src/services/word_check.py).

The key is only ever sent in the Authorization header. Every failure is a
QwenError whose code and message are fixed strings: they never contain the
key, the prompt, images, the provider's response or the model's output, and
the original exception is not chained, so a traceback can't leak them
either.
"""

import base64
import json
import os
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TypeVar

import requests

DEFAULT_BASE_URL = "https://token-plan.maas.qianwenaiapi.com/compatible-mode/v1"
DEFAULT_MODEL = "qwen3.8-flash"
TIMEOUT_SECONDS = 45.0
MAX_TOKENS = 4096

IMAGE_TYPES = frozenset({"image/png", "image/jpeg", "image/webp", "image/gif"})

T = TypeVar("T")


class QwenError(Exception):
    """A sanitized failure. `code` is one of the keys of MESSAGES."""

    MESSAGES = MappingProxyType(
        {
            "not_configured": "Qwen is not set up (no DASHSCOPE_API_KEY).",
            "bad_input": "The request to Qwen was not valid.",
            "timeout": "Qwen did not answer in time.",
            "unavailable": "Qwen could not be reached.",
            "auth": "Qwen rejected the API key.",
            "rate_limited": "Qwen is busy or the quota is used up. Try again later.",
            "bad_status": "Qwen returned an error.",
            "bad_reply": "Qwen returned an unusable answer.",
        }
    )

    def __init__(self, code: str):
        self.code = code
        super().__init__(self.MESSAGES[code])


@dataclass(frozen=True)
class QwenConfig:
    api_key: str = field(repr=False)  # never shown in logs or tracebacks
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "QwenConfig | None":
        """The configuration, or None when no key is set (Qwen is off)."""
        env = os.environ if environ is None else environ
        key = env.get("DASHSCOPE_API_KEY", "").strip()
        if not key:
            return None
        base_url = env.get("QWEN_BASE_URL", "").strip() or DEFAULT_BASE_URL
        model = env.get("QWEN_MODEL", "").strip() or DEFAULT_MODEL
        return cls(api_key=key, base_url=base_url.rstrip("/"), model=model)


@dataclass(frozen=True)
class QwenImage:
    data: bytes = field(repr=False)
    mime_type: str

    def data_url(self) -> str:
        if self.mime_type not in IMAGE_TYPES or not self.data:
            raise QwenError("bad_input")
        return f"data:{self.mime_type};base64,{base64.b64encode(self.data).decode('ascii')}"


def build_request_body(
    model: str, system_prompt: str, user_text: str, images: Sequence[QwenImage] = ()
) -> dict:
    """The chat-completions body: images first (as Base64 data URLs), then
    the text prompt."""
    if images:
        content: str | list = [
            {"type": "image_url", "image_url": {"url": image.data_url()}} for image in images
        ]
        content.append({"type": "text", "text": user_text})
    else:
        content = user_text
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content},
        ],
        "enable_thinking": False,
        "temperature": 0,
        "max_tokens": MAX_TOKENS,
        "response_format": {"type": "json_object"},
    }


def _error_for_status(status: int) -> QwenError:
    if status in (401, 403):
        return QwenError("auth")
    if status == 429:
        return QwenError("rate_limited")
    if status >= 500:
        return QwenError("unavailable")
    return QwenError("bad_status")


def _reply_object(response) -> dict:
    """The model's JSON object, or QwenError("bad_reply")."""
    try:
        body = response.json()
        choice = body["choices"][0]
        content = choice["message"]["content"]
        if choice.get("finish_reason") not in (None, "stop"):
            raise ValueError("cut short")
        if not isinstance(content, str):
            raise TypeError("content is not text")
        data = json.loads(content)
    except (KeyError, IndexError, TypeError, ValueError, AttributeError):
        raise QwenError("bad_reply") from None
    if not isinstance(data, dict):
        raise QwenError("bad_reply")
    return data


def complete_json(
    config: QwenConfig | None,
    system_prompt: str,
    user_text: str,
    validate: Callable[[dict], T],
    images: Sequence[QwenImage] = (),
    timeout: float = TIMEOUT_SECONDS,
) -> T:
    """Ask Qwen for one JSON object and return validate(object). Raises
    QwenError only; validate() signals a bad object with ValueError."""
    if config is None:
        raise QwenError("not_configured")
    body = build_request_body(config.model, system_prompt, user_text, images)
    try:
        response = requests.post(
            f"{config.base_url}/chat/completions",
            json=body,
            headers={"Authorization": f"Bearer {config.api_key}"},
            timeout=timeout,
        )
    except requests.Timeout:
        raise QwenError("timeout") from None
    except (requests.RequestException, OSError):
        raise QwenError("unavailable") from None

    if response.status_code != 200:
        raise _error_for_status(response.status_code)

    data = _reply_object(response)
    try:
        return validate(data)
    except (KeyError, TypeError, ValueError):
        raise QwenError("bad_reply") from None
