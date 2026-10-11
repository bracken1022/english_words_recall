"""Unit tests for the example-sentence evaluation tool (spec 021 T031),
run against a tiny fixture with a mocked local model."""

import json
import re
from unittest.mock import patch

import requests
import yaml

from src.tools.eval_examples import main

GOOD = {
    "zealous": {"sentence": "She is zealous about recycling.", "translation": "她热衷于回收利用。"},
    "give up": {"sentence": "Don't give up on your dreams.", "translation": "不要放弃你的梦想。"},
}


class _Resp:
    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return {"message": {"content": json.dumps(self._payload, ensure_ascii=False)}}


def _fake(replies):
    def post(url, json=None, timeout=None):
        word = re.search(r'English: "(.*)"', json["messages"][-1]["content"]).group(1)
        reply = replies[word]
        return _Resp(reply.pop(0) if isinstance(reply, list) else reply)

    return post


def _fixture(tmp_path):
    data = {
        "words": [
            {"english": "zealous", "chinese": "热心的", "pos": ["adj."]},
            {"english": "give up", "chinese": "放弃", "pos": ["phr. v."]},
        ]
    }
    path = tmp_path / "eval.yml"
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return path


def _run(tmp_path, replies, *extra):
    out_dir = tmp_path / "out"
    with patch("src.services.llm_client.requests.post", side_effect=_fake(replies)):
        status = main(["--fixture", str(_fixture(tmp_path)), "--out", str(out_dir), *extra])
    return status, out_dir


def test_passing_run_writes_review(tmp_path, capsys):
    status, out_dir = _run(tmp_path, dict(GOOD))
    assert status == 0
    out = capsys.readouterr().out
    assert "Valid examples: 2/2 (100%" in out
    assert out.strip().endswith("PASS (automatic checks) — now tick REVIEW.md")
    review = (out_dir / "REVIEW.md").read_text(encoding="utf-8")
    assert "| 1 | zealous | adj. | 热心的 | She is zealous about recycling. | 她热衷于回收利用。 | [ ] | [ ] |" in review
    assert "| 2 | give up |" in review
    assert "95%" in review and "unsafe" in review.lower()


def test_rejections_are_retried_once_and_counted(tmp_path, capsys):
    replies = dict(GOOD)
    replies["zealous"] = [
        {"sentence": "He works hard.", "translation": "他努力工作。"},
        {"sentence": "He works hard every day.", "translation": "他每天努力工作。"},
    ]
    status, out_dir = _run(tmp_path, replies)
    assert status == 1
    out = capsys.readouterr().out
    assert "Valid examples: 1/2 (50%" in out
    assert "doesn't use the word: 2" in out
    assert "NONE    zealous" in out
    review = (out_dir / "REVIEW.md").read_text(encoding="utf-8")
    assert "| 1 | zealous | adj. | 热心的 | (no valid example) |" in review


def test_sample_limits_the_words(tmp_path, capsys):
    status, out_dir = _run(tmp_path, dict(GOOD), "--sample", "1")
    assert status == 0
    assert "Valid examples: 1/1" in capsys.readouterr().out
    assert "give up" not in (out_dir / "REVIEW.md").read_text(encoding="utf-8")


def test_unavailable_model(tmp_path, capsys):
    def down(*_a, **_k):
        raise requests.ConnectionError()

    with patch("src.services.llm_client.requests.post", side_effect=down):
        status = main(["--fixture", str(_fixture(tmp_path)), "--out", str(tmp_path / "o")])
    assert status == 2
    assert "Local AI unavailable" in capsys.readouterr().err
