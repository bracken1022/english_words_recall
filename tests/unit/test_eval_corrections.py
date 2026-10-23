"""The word-correction quality check (spec 023 R10, SC-001/SC-002) and its
reviewed fixture. The checker is faked; the real run needs a key."""

import io
from pathlib import Path

import pytest

from src.lib.ipa import check_american_ipa, check_british_ipa, is_heteronym
from src.services.qwen_client import QwenError
from src.services.word_check import WordCheck
from src.tools import eval_corrections as ev

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "word_check_cases.yml"
CASES = ev.load_cases(FIXTURE)


# --- the fixture -------------------------------------------------------------------------


def test_fixture_has_50_errors_and_50_right_words():
    kinds = [c.kind for c in CASES]
    assert kinds.count("correct") == 50 and kinds.count("known_error") == 50
    errors = [c.error for c in CASES if c.kind == "known_error"]
    for field in ("ipa", "chinese", "pos"):
        assert errors.count(field) >= 16
    assert sum(is_heteronym(c.english) for c in CASES if c.kind == "correct") >= 5
    assert sum(" " in c.english for c in CASES if c.kind == "correct") >= 5


@pytest.mark.parametrize("case", CASES, ids=lambda c: f"{c.kind}-{c.english}-{c.error}")
def test_fixture_case_is_consistent(case):
    sent = ev.as_check(case.sent)
    wrong = ev.wrong_fields(sent, case)
    if case.kind == "correct":
        assert wrong == []
    else:
        assert wrong == [case.error]


@pytest.mark.parametrize("case", CASES, ids=lambda c: f"{c.kind}-{c.english}-{c.error}")
def test_accepted_ipa_fits_the_dialect(case):
    if is_heteronym(case.english):
        return
    check = check_british_ipa if case.dialect == "british" else check_american_ipa
    for ipa in case.accepted["ipa"]:
        assert check(ipa) == [], ipa


# --- scoring -----------------------------------------------------------------------------


def _case(kind, error=None, sent=None):
    return ev.Case(
        kind=kind,
        error=error,
        english="zealous",
        dialect="american",
        sent=sent or {"ipa": "ˈzeləs", "chinese": "嫉妒的", "pos": ["adj."]},
        accepted={
            "ipa": ["ˈzeləs"],
            "chinese_any": ["热心", "狂热"],
            "pos": ["adj."],
            "pos_ok": [],
        },
    )


def test_field_rules():
    case = _case("correct")
    assert ev.wrong_fields(WordCheck("ˈzeləs", "热心的；狂热的", ["adj."]), case) == []
    assert ev.wrong_fields(WordCheck("ˈzeləs", "嫉妒的", ["adj."]), case) == ["chinese"]
    assert ev.wrong_fields(WordCheck("ˈzɛləs", "热心的", ["adj."]), case) == ["ipa"]
    assert ev.wrong_fields(WordCheck("ˈzeləs", "热心的", ["adj.", "n."]), case) == ["pos"]
    assert ev.wrong_fields(WordCheck("ˈzeləs", "热心的", ["n."]), case) == ["pos"]


def _fake(answers):
    def check(english, ipa, chinese, pos, dialect):
        answer = answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer

    return check


def test_report_counts_fixed_errors_and_worse_words():
    cases = [_case("known_error", "chinese")] * 3 + [
        _case("correct", sent={"ipa": "ˈzeləs", "chinese": "热心的", "pos": ["adj."]})
    ] * 2
    answers = [
        WordCheck("ˈzeləs", "热心的", ["adj."]),  # fixed
        WordCheck("ˈzeləs", "嫉妒的", ["adj."]),  # not fixed
        QwenError("timeout"),  # not fixed, a failure
        WordCheck("ˈzeləs", "热心的；狂热的", ["adj."]),  # still right
        WordCheck("ˈzeləs", "热心的", ["n."]),  # made worse
    ]
    out = io.StringIO()
    report = ev.evaluate(cases, _fake(answers), out=out)
    assert (report.fixed, report.errors) == (1, 3)
    assert (report.worse, report.correct) == (1, 2)
    assert report.failures == {"timeout": 1}
    assert report.worsened == ["zealous (pos)"]
    assert not report.passed
    text = out.getvalue()
    assert "Errors fixed: 1/3" in text and "Right words made worse: 1/2" in text
    assert "timeout" in text


def test_targets():
    assert ev.Report(fixed=45, errors=50, worse=2, correct=50).passed
    assert not ev.Report(fixed=44, errors=50, worse=0, correct=50).passed
    assert not ev.Report(fixed=50, errors=50, worse=3, correct=50).passed


def test_main_without_a_key_exits_2(capsys):
    assert ev.main([str(FIXTURE)]) == 2
    assert "DASHSCOPE_API_KEY" in capsys.readouterr().err


def test_main_exit_status_follows_the_targets(monkeypatch, tmp_path):
    fixture = tmp_path / "cases.yml"
    fixture.write_text(
        "cases:\n"
        "  - {kind: known_error, error: chinese, english: zealous, dialect: american,\n"
        "     sent: {ipa: ˈzeləs, chinese: 嫉妒的, pos: [adj.]},\n"
        "     accepted: {ipa: [ˈzeləs], chinese_any: [热心], pos: [adj.], pos_ok: []}}\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-test")
    monkeypatch.setattr(
        ev.word_check, "check_word", lambda config, *a: WordCheck("ˈzeləs", "热心的", ["adj."])
    )
    assert ev.main([str(fixture)]) == 0
    monkeypatch.setattr(
        ev.word_check, "check_word", lambda config, *a: WordCheck("ˈzeləs", "嫉妒的", ["adj."])
    )
    assert ev.main([str(fixture)]) == 1
