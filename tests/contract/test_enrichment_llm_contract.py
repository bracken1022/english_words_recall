"""Contract tests for contracts/enrichment-llm-contract.md (spec 018):
request_enrichment() makes one local Ollama chat call per word, sends only
the word (and any learner-supplied meaning), reads only the two schema
keys — a Chinese meaning and alternates; pronunciations come from the
offline dictionary — and never raises: every failure becomes an outcome."""

import json
from unittest.mock import patch

import pytest
import requests

from src.services.enrichment_client import EnrichmentReply, request_enrichment

BASE = "http://localhost:11434"


class _FakeResponse:
    def __init__(self, status_code: int, json_data=None):
        self.status_code = status_code
        self._json_data = json_data if json_data is not None else {}

    def json(self):
        return self._json_data


def _content(payload) -> dict:
    text = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
    return {"message": {"role": "assistant", "content": text}}


def _reply(**overrides):
    payload = {"chinese": "热心的", "alternates": []}
    payload.update(overrides)
    return _FakeResponse(200, _content(payload))


def _call(english="zealous", supplied=None, model="qwen3:14b"):
    return request_enrichment(english, supplied or {}, base_url=BASE, model=model)


@patch("src.services.llm_client.requests.post")
def test_payload_shape(mock_post):
    mock_post.return_value = _reply()
    _call(model="m1")
    assert mock_post.call_count == 1
    assert mock_post.call_args.args[0] == f"{BASE}/api/chat"
    payload = mock_post.call_args.kwargs["json"]
    assert payload["model"] == "m1"
    assert payload["stream"] is False
    assert payload["think"] is False
    assert payload["options"]["temperature"] == 0
    assert payload["format"]["required"] == ["chinese", "alternates"]


@patch("src.services.llm_client.requests.post")
def test_user_message_has_word_and_optional_meaning(mock_post):
    mock_post.return_value = _reply()
    _call()
    user = mock_post.call_args.kwargs["json"]["messages"][-1]["content"]
    assert 'English: "zealous"' in user
    assert "Meaning:" not in user

    _call("receive", {"chinese": "收到"})
    user = mock_post.call_args.kwargs["json"]["messages"][-1]["content"]
    assert 'English: "receive"' in user
    assert 'Meaning: "收到"' in user


@patch("src.services.llm_client.requests.post")
def test_messages_carry_nothing_but_the_word(mock_post):
    mock_post.return_value = _reply()
    _call()
    text = json.dumps(mock_post.call_args.kwargs["json"]["messages"], ensure_ascii=False)
    assert "z-words" not in text
    assert ".txt" not in text


@patch("src.services.llm_client.requests.post")
def test_system_prompt_states_the_rules(mock_post):
    mock_post.return_value = _reply()
    _call()
    system = mock_post.call_args.kwargs["json"]["messages"][0]["content"]
    for phrase in ("；", "spelling variants", "Never give synonyms"):
        assert phrase in system
    assert "ipa" not in system.casefold()


@patch("src.services.llm_client.requests.post")
def test_valid_reply_is_ok_and_extra_keys_ignored(mock_post):
    mock_post.return_value = _reply(
        alternates=["zelous"], group="evil", english="zeal", ipa="ˈzeɪləs"
    )
    reply = _call()
    assert reply == EnrichmentReply(outcome="ok", chinese="热心的", alternates=["zelous"])
    for ignored in ("english", "group", "ipa"):
        assert not hasattr(reply, ignored)


@patch("src.services.llm_client.requests.post")
def test_connection_error_is_unavailable(mock_post):
    mock_post.side_effect = requests.ConnectionError()
    assert _call().outcome == "unavailable"


@patch("src.services.llm_client.requests.post")
def test_404_is_unavailable(mock_post):
    mock_post.return_value = _FakeResponse(404, {"error": "model not found"})
    assert _call().outcome == "unavailable"


@pytest.mark.parametrize(
    "response",
    [
        requests.Timeout(),
        _FakeResponse(500),
        _FakeResponse(200, {"done": True}),
        _FakeResponse(200, _content("not json")),
        _FakeResponse(200, _content("[]")),
        _FakeResponse(200, _content({"chinese": "热"})),
        _reply(chinese=3),
        _reply(alternates="tire"),
        _reply(alternates=["tire", 3]),
        _reply(chinese=None),
    ],
)
@patch("src.services.llm_client.requests.post")
def test_bad_replies(mock_post, response):
    if isinstance(response, Exception):
        mock_post.side_effect = response
    else:
        mock_post.return_value = response
    reply = _call()
    assert reply.outcome == "bad_reply"
    assert reply.detail


@patch("src.services.llm_client.requests.post")
def test_never_raises_on_unexpected_error(mock_post):
    mock_post.side_effect = requests.RequestException("boom")
    assert _call().outcome == "bad_reply"


# --- spec 019: part of speech in its own request (contracts/enrichment-pos-delta.md) ---

from src.services.enrichment_client import request_pos


def _pos_reply(**overrides):
    payload = {"pos": ["adj."]}
    payload.update(overrides)
    return _FakeResponse(200, _content(payload))


def _call_pos(english="zealous", chinese="热心的；热情的"):
    return request_pos(english, chinese, base_url=BASE, model="m1")


@patch("src.services.llm_client.requests.post")
def test_meaning_request_does_not_ask_for_pos(mock_post):
    mock_post.return_value = _reply()
    _call()
    payload = mock_post.call_args.kwargs["json"]
    assert "pos" not in payload["format"]["properties"]
    assert "part of speech" not in payload["messages"][0]["content"].casefold()


@patch("src.services.llm_client.requests.post")
def test_pos_request_shape(mock_post):
    mock_post.return_value = _pos_reply()
    _call_pos()
    assert mock_post.call_count == 1
    payload = mock_post.call_args.kwargs["json"]
    assert payload["model"] == "m1"
    assert payload["think"] is False
    assert payload["options"]["temperature"] == 0
    assert payload["format"]["required"] == ["pos"]
    user = payload["messages"][-1]["content"]
    assert 'English: "zealous"' in user
    assert 'Meaning: "热心的；热情的"' in user
    system = payload["messages"][0]["content"]
    for phrase in ("phr. v.", "Most words have exactly one", "only if one of the meanings"):
        assert phrase in system


@patch("src.services.llm_client.requests.post")
def test_pos_reply_is_read(mock_post):
    mock_post.return_value = _pos_reply(pos=["n.", "v."], group="x")
    reply = _call_pos()
    assert (reply.outcome, reply.pos) == ("ok", ["n.", "v."])


@pytest.mark.parametrize("bad", ["adj.", ["adj.", 3]])
@patch("src.services.llm_client.requests.post")
def test_bad_pos_type_is_bad_reply(mock_post, bad):
    mock_post.return_value = _pos_reply(pos=bad)
    assert _call_pos().outcome == "bad_reply"


@patch("src.services.llm_client.requests.post")
def test_pos_request_unavailable(mock_post):
    import requests

    mock_post.side_effect = requests.ConnectionError()
    assert _call_pos().outcome == "unavailable"
