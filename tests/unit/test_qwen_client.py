"""Qwen chat-completions client: configuration, request body, image
encoding, reply validation and sanitized errors. requests.post is faked;
no test reaches the network."""

import base64
import json
import traceback

import pytest
import requests

from src.services import qwen_client
from src.services.qwen_client import QwenConfig, QwenError, QwenImage, complete_json

KEY = "sk-secret-key-123"
CONFIG = QwenConfig(api_key=KEY, base_url="https://qwen.example/v1", model="qwen-test")
SYSTEM = "SYSTEM PROMPT TEXT"
USER = "USER PROMPT TEXT"


class FakeResponse:
    def __init__(self, status=200, body=None, raw=None):
        self.status_code = status
        self._body = body
        self._raw = raw

    def json(self):
        if self._raw is not None:
            return json.loads(self._raw)
        return self._body


def reply(content, finish_reason="stop"):
    return FakeResponse(
        body={"choices": [{"message": {"content": content}, "finish_reason": finish_reason}]}
    )


@pytest.fixture
def post(monkeypatch):
    """Records each call and answers with `post.response` (or raises
    `post.error`)."""

    class Post:
        def __init__(self):
            self.calls = []
            self.response = reply('{"ok": true}')
            self.error = None

        def __call__(self, url, **kwargs):
            self.calls.append((url, kwargs))
            if self.error:
                raise self.error
            return self.response

    fake = Post()
    monkeypatch.setattr(qwen_client.requests, "post", fake)
    return fake


def accept_any(data):
    return data


# --- configuration ------------------------------------------------------------


def test_config_from_env():
    config = QwenConfig.from_env(
        {
            "DASHSCOPE_API_KEY": f" {KEY} ",
            "QWEN_BASE_URL": "https://other.example/compatible-mode/v1/",
            "QWEN_MODEL": "qwen-other",
        }
    )
    assert config == QwenConfig(KEY, "https://other.example/compatible-mode/v1", "qwen-other")


def test_config_defaults():
    config = QwenConfig.from_env({"DASHSCOPE_API_KEY": KEY})
    assert config.base_url == "https://token-plan.maas.qianwenaiapi.com/compatible-mode/v1"
    assert config.model == "qwen3.8-flash"


@pytest.mark.parametrize("env", [{}, {"DASHSCOPE_API_KEY": "  "}])
def test_no_key_means_off(env):
    assert QwenConfig.from_env(env) is None


def test_reads_the_real_environment(monkeypatch):
    monkeypatch.setenv("DASHSCOPE_API_KEY", KEY)
    assert QwenConfig.from_env().api_key == KEY


def test_key_is_not_in_repr():
    assert KEY not in repr(CONFIG)


def test_not_configured_never_posts(post):
    with pytest.raises(QwenError) as err:
        complete_json(None, SYSTEM, USER, accept_any)
    assert err.value.code == "not_configured"
    assert post.calls == []


# --- request ------------------------------------------------------------------


def test_request_url_headers_and_body(post):
    assert complete_json(CONFIG, SYSTEM, USER, accept_any) == {"ok": True}
    [(url, kwargs)] = post.calls
    assert url == "https://qwen.example/v1/chat/completions"
    assert kwargs["headers"] == {"Authorization": f"Bearer {KEY}"}
    assert kwargs["timeout"] == 45
    assert kwargs["json"] == {
        "model": "qwen-test",
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": USER},
        ],
        "enable_thinking": False,
        "temperature": 0,
        "max_tokens": 4096,
        "response_format": {"type": "json_object"},
    }


def test_key_only_in_the_header(post):
    complete_json(CONFIG, SYSTEM, USER, accept_any)
    [(url, kwargs)] = post.calls
    assert KEY not in url
    assert KEY not in json.dumps(kwargs["json"])


def test_images_are_data_urls_before_the_text(post):
    png, jpeg = b"\x89PNG fake", b"\xff\xd8 fake"
    images = [QwenImage(png, "image/png"), QwenImage(jpeg, "image/jpeg")]
    complete_json(CONFIG, SYSTEM, USER, accept_any, images=images)
    content = post.calls[0][1]["json"]["messages"][1]["content"]
    assert content == [
        {
            "type": "image_url",
            "image_url": {"url": "data:image/png;base64," + base64.b64encode(png).decode()},
        },
        {
            "type": "image_url",
            "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(jpeg).decode()},
        },
        {"type": "text", "text": USER},
    ]


@pytest.mark.parametrize("image", [QwenImage(b"x", "image/svg+xml"), QwenImage(b"", "image/png")])
def test_bad_images_are_refused_before_sending(post, image):
    with pytest.raises(QwenError) as err:
        complete_json(CONFIG, SYSTEM, USER, accept_any, images=[image])
    assert err.value.code == "bad_input"
    assert post.calls == []


# --- replies ------------------------------------------------------------------


@pytest.mark.parametrize(
    "response",
    [
        FakeResponse(raw="not json"),
        FakeResponse(body={}),
        FakeResponse(body={"choices": []}),
        FakeResponse(body={"choices": [{"message": {}}]}),
        FakeResponse(body={"choices": [{"message": {"content": None}}]}),
        FakeResponse(body=["not", "an", "object"]),
        reply("not json at all"),
        reply('["a list"]'),
        reply('"a string"'),
        reply('{"ok": tr'),
        reply('{"ok": true}', finish_reason="length"),
    ],
)
def test_malformed_replies(post, response):
    post.response = response
    with pytest.raises(QwenError) as err:
        complete_json(CONFIG, SYSTEM, USER, accept_any)
    assert err.value.code == "bad_reply"


def test_validator_result_is_returned(post):
    post.response = reply('{"n": 2}')
    assert complete_json(CONFIG, SYSTEM, USER, lambda d: d["n"] * 10) == 20


@pytest.mark.parametrize("error", [ValueError("no"), KeyError("k"), TypeError("t")])
def test_validator_rejection_is_bad_reply(post, error):
    def reject(_data):
        raise error

    with pytest.raises(QwenError) as err:
        complete_json(CONFIG, SYSTEM, USER, reject)
    assert err.value.code == "bad_reply"


# --- provider errors and timeouts ---------------------------------------------


@pytest.mark.parametrize(
    ("status", "code"),
    [
        (400, "bad_status"),
        (401, "auth"),
        (403, "auth"),
        (404, "bad_status"),
        (429, "rate_limited"),
        (500, "unavailable"),
        (503, "unavailable"),
    ],
)
def test_provider_errors(post, status, code):
    post.response = FakeResponse(status, body={"error": {"message": f"invalid key {KEY}"}})
    with pytest.raises(QwenError) as err:
        complete_json(CONFIG, SYSTEM, USER, accept_any)
    assert err.value.code == code


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (requests.Timeout("read timed out"), "timeout"),
        (requests.ConnectTimeout("connect timed out"), "timeout"),
        (requests.ConnectionError("refused"), "unavailable"),
        (requests.RequestException("other"), "unavailable"),
    ],
)
def test_network_failures(post, error, code):
    post.error = error
    with pytest.raises(QwenError) as err:
        complete_json(CONFIG, SYSTEM, USER, accept_any)
    assert err.value.code == code


def test_custom_timeout_is_passed(post):
    complete_json(CONFIG, SYSTEM, USER, accept_any, timeout=5)
    assert post.calls[0][1]["timeout"] == 5


# --- nothing leaks --------------------------------------------------------------

SECRETS = (KEY, SYSTEM, USER, "MODEL OUTPUT", "PROVIDER TEXT", "IMAGEBYTES")


@pytest.mark.parametrize(
    "setup",
    [
        lambda p: setattr(p, "response", FakeResponse(401, body={"error": f"PROVIDER TEXT {KEY}"})),
        lambda p: setattr(p, "response", FakeResponse(raw="PROVIDER TEXT")),
        lambda p: setattr(p, "response", reply("MODEL OUTPUT")),
        lambda p: setattr(p, "response", reply('{"x": "MODEL OUTPUT"}', finish_reason="length")),
        lambda p: setattr(p, "error", requests.Timeout(f"PROVIDER TEXT {KEY}")),
        lambda p: setattr(p, "error", requests.ConnectionError(f"PROVIDER TEXT {KEY}")),
    ],
)
def test_errors_never_leak(post, setup):
    setup(post)

    def reject(data):
        raise ValueError(f"MODEL OUTPUT {data}")

    images = [QwenImage(b"IMAGEBYTES", "image/png")]
    with pytest.raises(QwenError) as err:
        complete_json(CONFIG, SYSTEM, USER, reject, images=images)
    shown = str(err.value) + repr(err.value) + "".join(traceback.format_exception(err.value))
    shown_b64 = base64.b64encode(b"IMAGEBYTES").decode()
    for secret in (*SECRETS, shown_b64):
        assert secret not in shown, secret
    assert err.value.__cause__ is None
    assert err.value.__context__ is None or err.value.__suppress_context__


def test_validator_message_never_leaks(post):
    post.response = reply('{"x": "MODEL OUTPUT"}')

    def reject(data):
        raise ValueError(f"bad {data}")

    with pytest.raises(QwenError) as err:
        complete_json(CONFIG, SYSTEM, USER, reject)
    assert "MODEL OUTPUT" not in "".join(traceback.format_exception(err.value))
