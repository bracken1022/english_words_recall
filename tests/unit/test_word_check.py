"""The word-check task for Qwen: prompt and strict validation of the
reply. The transport is faked."""

import json

import pytest

from src.services import qwen_client, word_check
from src.services.qwen_client import QwenConfig, QwenError
from src.services.word_check import WordCheck, check_word, validate

CONFIG = QwenConfig(api_key="sk-test", base_url="https://qwen.example/v1", model="qwen-test")
GOOD = {"ipa": "/ˈzeləs/", "chinese": " 热心的；狂热的 ", "pos": ["adj."]}


def test_valid_reply_is_normalised():
    assert validate(dict(GOOD), "american") == WordCheck(
        ipa="ˈzeləs", chinese="热心的；狂热的", pos=["adj."]
    )


def test_pos_spellings_are_normalised():
    assert validate({**GOOD, "pos": ["noun", "verb"]}, "british").pos == ["n.", "v."]


@pytest.mark.parametrize(
    "data",
    [
        {"ipa": "ˈzeləs", "chinese": "热心的"},  # missing pos
        {**GOOD, "english": "jealous"},  # extra key
        {**GOOD, "ipa": ""},
        {**GOOD, "ipa": "123"},
        {**GOOD, "ipa": None},
        {**GOOD, "ipa": ["ˈzeləs"]},
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
        validate(data, "american")


def test_the_ipa_must_fit_the_dialect():
    # Rhotic r is American; ɒ is British.
    with pytest.raises(ValueError):
        validate({**GOOD, "ipa": "ˈteɪlər"}, "british")
    with pytest.raises(ValueError):
        validate({**GOOD, "ipa": "hɒt"}, "american")
    assert validate({**GOOD, "ipa": "ˈteɪlə"}, "british").ipa == "ˈteɪlə"
    assert validate({**GOOD, "ipa": "ˈteɪlər"}, "american").ipa == "ˈteɪlər"


def test_unknown_dialect_is_refused():
    with pytest.raises(ValueError):
        word_check.system_prompt("australian")
    with pytest.raises(ValueError):
        validate(dict(GOOD), "australian")


def test_prompt_names_the_dialect():
    assert "British" in word_check.system_prompt("british")
    assert "Oxford" in word_check.system_prompt("british")
    assert "American" in word_check.system_prompt("american")
    assert "Do not change" in word_check.system_prompt("american")


def test_only_the_five_word_lines_are_sent():
    text = word_check.user_text("zealous", "ˈzeləs", "嫉妒的", ["n."], "british")
    assert text.splitlines() == [
        'English: "zealous"',
        "Dialect: British",
        'Current IPA: "ˈzeləs"',
        'Current Chinese: "嫉妒的"',
        'Current parts of speech: "n."',
    ]
    assert "Dialect: American" in word_check.user_text("zealous", None, "", [], "american")


def _reply(monkeypatch, content: dict, calls: list | None = None):
    class Response:
        status_code = 200

        def json(self):
            text = json.dumps(content, ensure_ascii=False)
            return {"choices": [{"message": {"content": text}, "finish_reason": "stop"}]}

    def post(url, **kwargs):
        if calls is not None:
            calls.append(kwargs["json"])
        return Response()

    monkeypatch.setattr(qwen_client.requests, "post", post)


def test_check_word_end_to_end(monkeypatch):
    calls = []
    _reply(monkeypatch, GOOD, calls)
    result = check_word(CONFIG, "zealous", None, "嫉妒的", [], "british")
    assert result == WordCheck("ˈzeləs", "热心的；狂热的", ["adj."])
    assert calls[0]["messages"][0]["content"] == word_check.system_prompt("british")
    assert "Dialect: British" in calls[0]["messages"][1]["content"]
    assert '"zealous"' in calls[0]["messages"][1]["content"]


def test_heteronym_keeps_its_current_ipa(monkeypatch):
    # Even a wrong-dialect IPA in the answer doesn't reject the meaning.
    _reply(monkeypatch, {"ipa": "ˈrekərd", "chinese": "记录；唱片", "pos": ["n."]})
    result = check_word(CONFIG, "record", "ˈrekɔːd", "录音", ["v."], "british")
    assert result == WordCheck("ˈrekɔːd", "记录；唱片", ["n."])


def test_heteronym_still_validates_the_rest(monkeypatch):
    _reply(monkeypatch, {"ipa": "ˈrekɔːd", "chinese": "", "pos": ["n."]})
    with pytest.raises(QwenError) as err:
        check_word(CONFIG, "record", "ˈrekɔːd", "记录", ["n."], "british")
    assert err.value.code == "bad_reply"


def test_unusable_reply_is_bad_reply(monkeypatch):
    _reply(monkeypatch, {**GOOD, "pos": []})
    with pytest.raises(QwenError) as err:
        check_word(CONFIG, "zealous", None, None, [], "american")
    assert err.value.code == "bad_reply"


def test_wrong_dialect_reply_is_bad_reply(monkeypatch):
    _reply(monkeypatch, {**GOOD, "ipa": "ˈteɪlər"})
    with pytest.raises(QwenError) as err:
        check_word(CONFIG, "tailor", "ˈteɪlə", "裁缝", ["n."], "british")
    assert err.value.code == "bad_reply"


def test_off_without_a_key():
    with pytest.raises(QwenError) as err:
        check_word(None, "zealous", None, None, [], "american")
    assert err.value.code == "not_configured"
