"""The word-check task for Qwen: prompt and strict validation of the
reply. The transport is faked."""

import json

import pytest

from src.services import qwen_client, word_check
from src.services.qwen_client import QwenConfig, QwenError
from src.services.word_check import WordCheck, check_word, validate

CONFIG = QwenConfig(api_key="sk-test", base_url="https://qwen.example/v1", model="qwen-test")
GOOD = {"ipa": "/ˈzɛləs/", "chinese": " 热心的；狂热的 ", "pos": ["adj."]}


def test_valid_reply_is_normalised():
    assert validate(dict(GOOD)) == WordCheck(ipa="ˈzɛləs", chinese="热心的；狂热的", pos=["adj."])


def test_pos_spellings_are_normalised():
    assert validate({**GOOD, "pos": ["noun", "verb"]}).pos == ["n.", "v."]


@pytest.mark.parametrize(
    "data",
    [
        {"ipa": "ˈzɛləs", "chinese": "热心的"},  # missing pos
        {**GOOD, "english": "jealous"},  # extra key
        {**GOOD, "ipa": ""},
        {**GOOD, "ipa": "123"},
        {**GOOD, "ipa": None},
        {**GOOD, "ipa": ["ˈzɛləs"]},
        {**GOOD, "chinese": ""},
        {**GOOD, "chinese": "   "},
        {**GOOD, "chinese": 5},
        {**GOOD, "chinese": "很" * 61},
        {**GOOD, "pos": []},
        {**GOOD, "pos": "adj."},
        {**GOOD, "pos": ["adjectivey"]},
        {**GOOD, "pos": [1]},
    ],
)
def test_bad_replies_are_rejected(data):
    with pytest.raises(ValueError):
        validate(data)


def test_prompt_carries_the_word_and_current_values():
    text = word_check.user_text("zealous", "ˈzɛləs", "嫉妒的", ["n."])
    assert '"zealous"' in text and "ˈzɛləs" in text and "嫉妒的" in text and "n." in text
    assert "Do not change" in word_check.SYSTEM_PROMPT


def test_check_word_end_to_end(monkeypatch):
    calls = []

    class Response:
        status_code = 200

        def json(self):
            content = json.dumps(GOOD, ensure_ascii=False)
            return {"choices": [{"message": {"content": content}, "finish_reason": "stop"}]}

    def post(url, **kwargs):
        calls.append(kwargs["json"])
        return Response()

    monkeypatch.setattr(qwen_client.requests, "post", post)
    result = check_word(CONFIG, "zealous", None, "嫉妒的", [])
    assert result == WordCheck("ˈzɛləs", "热心的；狂热的", ["adj."])
    assert calls[0]["messages"][0]["content"] == word_check.SYSTEM_PROMPT
    assert '"zealous"' in calls[0]["messages"][1]["content"]


def test_unusable_reply_is_bad_reply(monkeypatch):
    class Response:
        status_code = 200

        def json(self):
            content = json.dumps({**GOOD, "pos": []})
            return {"choices": [{"message": {"content": content}, "finish_reason": "stop"}]}

    monkeypatch.setattr(qwen_client.requests, "post", lambda url, **kw: Response())
    with pytest.raises(QwenError) as err:
        check_word(CONFIG, "zealous", None, None, [])
    assert err.value.code == "bad_reply"


def test_off_without_a_key():
    with pytest.raises(QwenError) as err:
        check_word(None, "zealous", None, None, [])
    assert err.value.code == "not_configured"
