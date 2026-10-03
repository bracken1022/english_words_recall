"""Unit tests for the enrichment evaluation tool (spec 018 T049), run
against a tiny fixture with a mocked local model."""

import json
from unittest.mock import patch

import requests
import yaml

from src.tools.eval_enrichment import main

REPLIES = {
    "zealous": {"chinese": "热心的；热情的", "alternates": ["enthusiastic"]},
    "record": {"chinese": "记录", "alternates": []},
    "colour": {"chinese": "颜色", "alternates": ["color"]},
}


class _Resp:
    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return {"message": {"content": json.dumps(self._payload, ensure_ascii=False)}}


def _fake(replies):
    def post(url, json=None, timeout=None):
        word = json["messages"][-1]["content"].split('"')[1]
        return _Resp(replies[word])

    return post


def _fixture(tmp_path, **overrides):
    data = {
        "words": [{"english": "zealous", "ipa": "ˈzeləs", "chinese_any": ["热心"]}],
        "heteronyms": ["record"],
        "traps": [{"english": "zealous", "forbidden": ["enthusiastic"]}],
        "variants": [{"english": "colour", "expected": "color"}],
    }
    data.update(overrides)
    path = tmp_path / "eval.yml"
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return path


def test_passing_report(tmp_path, capsys):
    with patch("src.services.llm_client.requests.post", side_effect=_fake(REPLIES)):
        assert main(["--fixture", str(_fixture(tmp_path))]) == 0
    out = capsys.readouterr().out
    assert "IPA:            1/1 match (100%)" in out
    assert "Heteronyms:     1/1 flagged" in out
    assert "Synonym traps:  0 leaked" in out
    assert "Variants:       1/1 found" in out
    assert "Invalid output: 0" in out
    assert out.strip().endswith("PASS")


def test_wrong_ipa_fails(tmp_path, capsys):
    words = [{"english": "zealous", "ipa": "ˈziːləs", "chinese_any": ["热心"]}]
    with patch("src.services.llm_client.requests.post", side_effect=_fake(REPLIES)):
        assert main(["--fixture", str(_fixture(tmp_path, words=words))]) == 1
    out = capsys.readouterr().out
    assert "WRONG   zealous: /ˈzeləs/, expected /ˈziːləs/" in out
    assert "FAIL" in out


def test_missing_variant_fails(tmp_path, capsys):
    replies = {**REPLIES, "colour": {**REPLIES["colour"], "alternates": []}}
    with patch("src.services.llm_client.requests.post", side_effect=_fake(replies)):
        assert main(["--fixture", str(_fixture(tmp_path))]) == 1
    assert "variant colour: expected color, got none" in capsys.readouterr().out


def test_unavailable_exits_2(tmp_path, capsys):
    with patch("src.services.llm_client.requests.post", side_effect=requests.ConnectionError()):
        assert main(["--fixture", str(_fixture(tmp_path))]) == 2
    assert "Local AI unavailable" in capsys.readouterr().err


def test_monosyllable_stress_mark_is_not_a_mismatch(tmp_path, capsys):
    replies = {**REPLIES, "bird": {"chinese": "鸟", "alternates": []}}
    words = [{"english": "bird", "ipa": "ˈbɜːrd", "chinese_any": ["鸟"]}]
    with patch("src.services.llm_client.requests.post", side_effect=_fake(replies)):
        assert main(["--fixture", str(_fixture(tmp_path, words=words))]) == 0
    assert "IPA:            1/1 match" in capsys.readouterr().out


def test_comparable_accepts_dictionary_conventions_only():
    from src.tools.eval_enrichment import _comparable

    same = [
        ("ˈvaɪtəmən", "ˈvaɪtəmɪn"),
        ("ˈkɑːfi", "ˈkɔːfi"),
        ("ˈneɪʃn", "ˈneɪʃən"),
        ("ˌɪˈnevətəbl", "ɪnˈevɪtəbl"),
        ("ˈlaɪˌbreri", "ˈlaɪbreri"),
        ("bɜːrd", "ˈbɜːrd"),
    ]
    for a, b in same:
        assert _comparable(a) == _comparable(b), (a, b)
    different = [
        ("ˈzeɪləs", "ˈzeləs"),
        ("ˈvɪtəmɪn", "ˈvaɪtəmɪn"),
        ("təˈmɑːtoʊ", "təˈmeɪtoʊ"),
        ("ˈæbəndənt", "əˈbʌndənt"),
        ("dɑːns", "dæns"),
    ]
    for a, b in different:
        assert _comparable(a) != _comparable(b), (a, b)


def test_attested_variants_count_as_matches(tmp_path, capsys):
    replies = {**REPLIES, "leisure": {"chinese": "空闲", "alternates": []}}
    words = [{"english": "leisure", "ipa": "ˈliːʒər", "ipa_also": ["ˈleʒər"], "chinese_any": ["空闲"]}]
    with patch("src.services.llm_client.requests.post", side_effect=_fake(replies)):
        assert main(["--fixture", str(_fixture(tmp_path, words=words))]) == 0
    assert "IPA:            1/1 match" in capsys.readouterr().out
