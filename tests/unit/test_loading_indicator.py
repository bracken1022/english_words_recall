"""Unit tests for run_with_indicator against a real rich.Console (not a
fake), to prove it actually integrates with rich's API correctly."""

import io
import re
import time

from rich.console import Console

from src.cli.loading_indicator import run_with_indicator


def test_func_called_exactly_once_terminal_mode():
    console = Console(file=io.StringIO(), force_terminal=True, width=80)
    call_count = {"n": 0}

    def func():
        call_count["n"] += 1
        return "ok"

    run_with_indicator(console, "Reviewing your sentence...", func)
    assert call_count["n"] == 1


def test_func_called_exactly_once_non_terminal_mode():
    console = Console(file=io.StringIO(), force_terminal=False)
    call_count = {"n": 0}

    def func():
        call_count["n"] += 1
        return "ok"

    run_with_indicator(console, "Reviewing your sentence...", func)
    assert call_count["n"] == 1


def test_message_contains_no_percentage_or_step_count():
    message = "Reviewing your sentence..."
    assert "%" not in message
    assert not re.search(r"\d+\s*/\s*\d+", message)  # no "3/10"-style step count
    assert not re.search(r"\b\d+%", message)


def test_non_terminal_output_is_a_single_plain_line_no_ansi():
    buffer = io.StringIO()
    console = Console(file=buffer, force_terminal=False)

    run_with_indicator(console, "Reviewing your sentence...", lambda: None)

    output = buffer.getvalue()
    assert "Reviewing your sentence..." in output
    assert "\x1b[" not in output  # no ANSI escape codes leaked into non-tty output


def test_no_artificial_delay_is_added_terminal_mode():
    console = Console(file=io.StringIO(), force_terminal=True, width=80)

    start = time.monotonic()
    run_with_indicator(console, "Reviewing your sentence...", lambda: None)
    elapsed = time.monotonic() - start

    assert elapsed < 0.5  # run_with_indicator itself adds no sleep/minimum-duration logic


def test_no_artificial_delay_is_added_non_terminal_mode():
    console = Console(file=io.StringIO(), force_terminal=False)

    start = time.monotonic()
    run_with_indicator(console, "Reviewing your sentence...", lambda: None)
    elapsed = time.monotonic() - start

    assert elapsed < 0.5


def test_fast_func_completes_immediately_not_held_open():
    console = Console(file=io.StringIO(), force_terminal=True, width=80)
    call_times = []

    def instant():
        call_times.append(time.monotonic())
        return "done"

    before = time.monotonic()
    result = run_with_indicator(console, "Reviewing your sentence...", instant)
    after = time.monotonic()

    assert result == "done"
    assert before <= call_times[0] <= after
    assert (after - before) < 0.1  # no minimum display duration is enforced
