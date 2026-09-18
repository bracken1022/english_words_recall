import time
from unittest.mock import patch

from src.cli import session as session_module
from src.cli.loading_indicator import run_with_indicator
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


@patch("src.cli.session.run_with_indicator", wraps=run_with_indicator)
@patch("src.cli.session.request_correction")
def test_indicator_is_active_for_the_duration_of_a_slow_review_call(mock_request, mock_indicator, capsys):
    def slow_correction(*args, **kwargs):
        time.sleep(0.05)
        return _fake_correction(needs_correction=False)

    mock_request.side_effect = slow_correction

    start = time.monotonic()
    run_sentence_step("receive", sentence_input=lambda: "I received a gift.", base_url="x", model="m")
    elapsed = time.monotonic() - start

    mock_indicator.assert_called_once()
    call_args = mock_indicator.call_args
    assert call_args.args[0] is session_module.console
    assert call_args.args[2] is mock_request
    assert elapsed >= 0.05  # the wrapped call's delay actually happened inside run_with_indicator

    out = capsys.readouterr().out
    assert "already correct" in out.lower()


class _OrderTrackingConsole:
    """A minimal fake console recording enter/exit/print order, used to
    prove the indicator is closed before any feedback text is printed."""

    def __init__(self, is_terminal: bool = True):
        self.is_terminal = is_terminal
        self.events: list[str] = []

    def status(self, message, spinner="dots"):
        events = self.events

        class _Status:
            def __enter__(self_inner):
                events.append("indicator-enter")
                return self_inner

            def __exit__(self_inner, exc_type, exc, tb):
                events.append("indicator-exit")
                return False

        return _Status()

    def print(self, *args, **kwargs):
        self.events.append("print")


@patch("src.cli.session.request_correction")
def test_indicator_closed_before_message_for_every_outcome(mock_request, monkeypatch):
    outcomes = [
        _fake_correction(needs_correction=True, corrected="X", explanation="Y"),
        _fake_correction(needs_correction=False),
        _fake_correction(uses_expression=False, needs_correction=False),
        CorrectionResult(available=False, uses_expression=None, needs_correction=None, corrected=None, explanation=None),
    ]

    for outcome in outcomes:
        mock_request.return_value = outcome
        fake_console = _OrderTrackingConsole(is_terminal=True)
        monkeypatch.setattr(session_module, "console", fake_console)

        run_sentence_step("receive", sentence_input=lambda: "I received a gift.", base_url="x", model="m")

        assert "indicator-enter" in fake_console.events
        assert "indicator-exit" in fake_console.events
        enter_index = fake_console.events.index("indicator-enter")
        exit_index = fake_console.events.index("indicator-exit")
        # no feedback/result print is interleaved with the indicator while
        # it's active — the indicator is always closed before any print
        # that happens after it starts
        print_indices = [i for i, e in enumerate(fake_console.events) if e == "print"]
        interleaved = [i for i in print_indices if enter_index < i < exit_index]
        assert interleaved == [], fake_console.events
        # and at least one result-related print happens only after the
        # indicator has fully closed
        assert any(i > exit_index for i in print_indices), fake_console.events


@patch("src.cli.session.request_correction")
def test_non_interactive_console_prints_once_with_no_status_call(mock_request):
    mock_request.return_value = _fake_correction(needs_correction=False)
    fake_console = _OrderTrackingConsole(is_terminal=False)
    with patch.object(session_module, "console", fake_console):
        run_sentence_step("receive", sentence_input=lambda: "I received a gift.", base_url="x", model="m")

    assert "indicator-enter" not in fake_console.events
    assert "indicator-exit" not in fake_console.events
    assert fake_console.events[0] == "print"  # the "Write a sentence..." prompt line comes first
    assert fake_console.events.count("print") >= 3  # prompt line, fallback message line, result line
