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


# --- spec 019: part-of-speech accuracy -----------------------------------------


def _pos_fixture(tmp_path, pos, pos_ok=None):
    word = {"english": "zealous", "ipa": "ˈzeləs", "chinese_any": ["热心"], "pos": pos}
    if pos_ok:
        word["pos_ok"] = pos_ok
    return _fixture(tmp_path, words=[word])


def _with_pos(labels, chinese="热心的"):
    return {**REPLIES, "zealous": {**REPLIES["zealous"], "chinese": chinese, "pos": labels}}


def test_pos_match_passes(tmp_path, capsys):
    with patch("src.services.llm_client.requests.post", side_effect=_fake(_with_pos(["adj."]))):
        assert main(["--fixture", str(_pos_fixture(tmp_path, ["adj."]))]) == 0
    out = capsys.readouterr().out
    assert "Part of speech: 1/1 match or flagged (100%" in out
    assert "POS notes left in meanings: 0" in out


def test_pos_outside_reference_fails(tmp_path, capsys):
    with patch("src.services.llm_client.requests.post", side_effect=_fake(_with_pos(["n."]))):
        assert main(["--fixture", str(_pos_fixture(tmp_path, ["adj."]))]) == 1
    assert "pos     zealous: [n.], expected [adj.]" in capsys.readouterr().out


def test_pos_ok_labels_are_accepted(tmp_path, capsys):
    replies = _with_pos(["adj.", "n."])
    with patch("src.services.llm_client.requests.post", side_effect=_fake(replies)):
        assert main(["--fixture", str(_pos_fixture(tmp_path, ["adj."], ["n."]))]) == 0


def test_flagged_pos_counts_as_safe(tmp_path, capsys):
    with patch("src.services.llm_client.requests.post", side_effect=_fake(_with_pos(["verbish"]))):
        assert main(["--fixture", str(_pos_fixture(tmp_path, ["adj."]))]) == 0
    assert "1 flagged" in capsys.readouterr().out


def test_phrase_with_acceptable_single_class_counts(tmp_path, capsys):
    # 2026-10-05 decision: for a multi-word expression, labels that are all
    # in pos ∪ pos_ok count (tend to → v.), as OALD files such phrases under
    # the verb. Single words still need one label from pos.
    words = [{"english": "tend to", "ipa": "ˈtend tə", "chinese_any": ["倾向"],
              "pos": ["phr. v."], "pos_ok": ["v.", "phr."]}]  # fmt: skip
    replies = {"tend to": {"chinese": "倾向于", "alternates": [], "pos": ["v."]}}
    with patch("src.services.llm_client.requests.post", side_effect=_fake(replies)):
        assert main(["--fixture", str(_fixture(tmp_path, words=words, traps=[], variants=[], heteronyms=[]))]) == 0
    assert "Part of speech: 1/1 match or flagged" in capsys.readouterr().out


def test_single_word_still_needs_a_required_label(tmp_path, capsys):
    words = [{"english": "figure", "ipa": "ˈfɪɡjər", "chinese_any": ["数字"],
              "pos": ["n."], "pos_ok": ["v."]}]  # fmt: skip
    replies = {"figure": {"chinese": "数字", "alternates": [], "pos": ["v."]}}
    with patch("src.services.llm_client.requests.post", side_effect=_fake(replies)):
        assert main(["--fixture", str(_fixture(tmp_path, words=words, traps=[], variants=[], heteronyms=[]))]) == 1
