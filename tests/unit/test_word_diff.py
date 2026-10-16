"""Comparing a sentence-recall attempt with the real sentence (spec 022,
FR-012, contracts/word-diff.md). The cases are a reviewed fixture
(SC-007, Constitution II)."""

from pathlib import Path

import pytest
import yaml

from src.lib.word_diff import compare

CASES = yaml.safe_load(
    (Path(__file__).parents[1] / "fixtures" / "word_diff_cases.yml").read_text(encoding="utf-8")
)["cases"]


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_reviewed_case(case):
    result = compare(case["attempt"], case["sentence"])
    if case.get("none"):
        assert result is None
        return
    assert [m.word for m in result.sentence if m.status == "missing"] == case["missing"]
    assert [m.word for m in result.attempt if m.status == "extra"] == case["extra"]
    assert {m.status for m in result.sentence} <= {"same", "missing"}
    assert {m.status for m in result.attempt} <= {"same", "extra"}


@pytest.mark.parametrize("attempt", ["", "   \n", "\t"])
def test_blank_attempt_gives_no_comparison(attempt):
    assert compare(attempt, "She is honest.") is None


def test_words_kept_as_written_and_in_order():
    result = compare("she IS on the team,", "She is on the team.")
    assert [m.word for m in result.sentence] == ["She", "is", "on", "the", "team."]
    assert [m.word for m in result.attempt] == ["she", "IS", "on", "the", "team,"]
    assert all(m.status == "same" for m in result.sentence + result.attempt)


def test_punctuation_only_words_are_dropped():
    result = compare("I was late — sorry !", "I was late, sorry.")
    assert [m.word for m in result.attempt] == ["I", "was", "late", "sorry"]


def test_deterministic():
    args = ("She was a zealous fan of the team.", "She is a zealous supporter of the team.")
    assert compare(*args) == compare(*args)


def test_to_json_shape():
    data = compare("She is a zelous supporter of team", "She is a zealous supporter of the team.")
    data = data.to_json()
    assert data["sentence"][3] == {"word": "zealous", "status": "missing"}
    assert data["attempt"][3] == {"word": "zelous", "status": "extra"}
    assert set(data) == {"sentence", "attempt"}
