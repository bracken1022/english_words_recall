"""Contract tests for src/services/example_client.py (spec 021, research
R3): one local chat request per example, checked before it is used."""

import json
from unittest.mock import patch

import pytest
import requests

from src.services.example_client import ExampleReply, request_example, validate_example

BASE = "http://localhost:11434"


class _Resp:
    def __init__(self, status=200, payload=None):
        self.status_code = status
        self._payload = payload

    def json(self):
        return {"message": {"content": json.dumps(self._payload, ensure_ascii=False)}}


GOOD = {"sentence": "She is a zealous supporter of the team.", "translation": "她是球队的狂热支持者。"}


def _call():
    return request_example("zealous", "热心的", ["adj."], base_url=BASE, model="m1")


@patch("src.services.llm_client.requests.post")
def test_request_shape(mock_post):
    mock_post.return_value = _Resp(payload=GOOD)
    _call()
    payload = mock_post.call_args.kwargs["json"]
    assert payload["model"] == "m1"
    assert payload["think"] is False
    assert payload["options"]["temperature"] == 0.7
    assert payload["format"]["required"] == ["sentence", "translation"]
    user = payload["messages"][-1]["content"]
    assert 'English: "zealous"' in user and 'Meaning: "热心的"' in user and "adj." in user
    system = payload["messages"][0]["content"]
    for phrase in ("natural", "at most 20 words", "everyday", "family"):
        assert phrase in system


@patch("src.services.llm_client.requests.post")
def test_ok_reply(mock_post):
    mock_post.return_value = _Resp(payload=GOOD)
    assert _call() == ExampleReply("ok", GOOD["sentence"], GOOD["translation"])


@patch("src.services.llm_client.requests.post")
def test_unavailable(mock_post):
    mock_post.side_effect = requests.ConnectionError()
    assert _call().outcome == "unavailable"


@pytest.mark.parametrize("payload", [{"sentence": "x"}, {"sentence": 3, "translation": "中"}, "nope"])
@patch("src.services.llm_client.requests.post")
def test_bad_reply(mock_post, payload):
    mock_post.return_value = _Resp(payload=payload)
    assert _call().outcome == "bad_reply"


def test_validate_accepts_good_pair():
    assert validate_example("zealous", GOOD["sentence"], GOOD["translation"]) == (True, None)


@pytest.mark.parametrize(
    "sentence, translation",
    [
        ("She is a keen supporter of the team.", "她是球队的支持者。"),  # word missing
        ("I like it. It is zealous.", "我喜欢。"),  # two sentences
        ("She is zealous\nabout it.", "她很热心。"),  # newline
        ("Zealous.", "热心。"),  # too short
        ("She is " + "very " * 20 + "zealous.", "她非常热心。"),  # too long
        ("She is zealous.", "She is zealous."),  # no Chinese
        ("She is zealous.", "她" * 61),  # translation too long
    ],
)
def test_validate_rejects(sentence, translation):
    ok, reason = validate_example("zealous", sentence, translation)
    assert not ok
    assert reason


def test_validate_rejects_unclean(monkeypatch):
    from src.services import example_client

    monkeypatch.setattr(example_client, "is_clean", lambda text, allow=(): "zealous" not in text)
    assert validate_example("zealous", GOOD["sentence"], GOOD["translation"])[0] is False


@patch("src.services.llm_client.requests.post")
def test_request_asks_for_a_different_sentence(mock_post):
    mock_post.return_value = _Resp(payload={"sentence": "Our rent went up.", "translation": "房租涨了。"})
    request_example("rent", "租金", ["n."], "http://x", "m", avoid="The rent is due.")
    content = mock_post.call_args.kwargs["json"]["messages"][-1]["content"]
    assert 'Write a different sentence from: "The rent is due."' in content
