from unittest.mock import patch

from src.cli.session import run_sentence_step
from src.services.llm_client import CorrectionResult


def _fake_correction(**overrides):
    base = {
        "available": True,
        "uses_expression": True,
        "needs_correction": False,
        "corrected": None,
        "explanation": None,
    }
    base.update(overrides)
    return CorrectionResult(**base)


@patch("src.cli.session.request_correction")
def test_needs_correction_shows_corrected_and_explanation(mock_request, capsys):
    mock_request.return_value = _fake_correction(
        needs_correction=True, corrected="I received a gift.", explanation="Past tense needed."
    )
    feedback = run_sentence_step("receive", sentence_input=lambda: "I recieve a gift.", base_url="x", model="m")
    out = capsys.readouterr().out
    assert "I received a gift." in out
    assert "Past tense needed." in out
    assert feedback is not None


@patch("src.cli.session.request_correction")
def test_already_correct_sentence_shows_no_invented_changes(mock_request, capsys):
    mock_request.return_value = _fake_correction(needs_correction=False)
    run_sentence_step("receive", sentence_input=lambda: "I received a gift.", base_url="x", model="m")
    out = capsys.readouterr().out
    assert "already correct" in out.lower()


@patch("src.cli.session.request_correction")
def test_missing_target_expression_tells_learner(mock_request, capsys):
    mock_request.return_value = _fake_correction(uses_expression=False, needs_correction=False)
    run_sentence_step("receive", sentence_input=lambda: "I am happy today.", base_url="x", model="m")
    out = capsys.readouterr().out
    assert "missing" in out.lower() or "does not use" in out.lower()


@patch("src.cli.session.request_correction")
def test_llm_unavailable_tells_learner_and_does_not_raise(mock_request, capsys):
    mock_request.return_value = CorrectionResult(
        available=False, uses_expression=None, needs_correction=None, corrected=None, explanation=None
    )
    feedback = run_sentence_step("receive", sentence_input=lambda: "I received a gift.", base_url="x", model="m")
    out = capsys.readouterr().out
    assert "unavailable" in out.lower()
    assert feedback is not None
