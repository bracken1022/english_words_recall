"""Contract test for contracts/loading-indicator-contract.md (spec 002)."""


from src.cli.loading_indicator import run_with_indicator


class _FakeStatusCall:
    def __init__(self, calls, message, spinner):
        self.calls = calls
        self.message = message
        self.spinner = spinner

    def __enter__(self):
        self.calls.append(("enter", self.message, self.spinner))
        return self

    def __exit__(self, exc_type, exc, tb):
        self.calls.append(("exit", self.message, self.spinner))
        return False


class _FakeConsole:
    def __init__(self, is_terminal: bool):
        self.is_terminal = is_terminal
        self.calls: list = []

    def status(self, message, spinner="dots"):
        return _FakeStatusCall(self.calls, message, spinner)

    def print(self, message):
        self.calls.append(("print", message))


def test_terminal_mode_enters_status_before_calling_func():
    console = _FakeConsole(is_terminal=True)
    order = []

    def func():
        order.append("func-called")
        return "result"

    result = run_with_indicator(console, "Reviewing your sentence...", func)

    assert result == "result"
    assert console.calls[0] == ("enter", "Reviewing your sentence...", "dots")
    assert order == ["func-called"]
    assert console.calls[-1] == ("exit", "Reviewing your sentence...", "dots")


def test_non_terminal_mode_prints_once_and_never_calls_status():
    console = _FakeConsole(is_terminal=False)

    def func():
        return 42

    result = run_with_indicator(console, "Reviewing your sentence...", func)

    assert result == 42
    assert console.calls == [("print", "Reviewing your sentence...")]


def test_return_value_passed_through_unchanged():
    console = _FakeConsole(is_terminal=True)
    sentinel = object()
    result = run_with_indicator(console, "msg", lambda: sentinel)
    assert result is sentinel


def test_exception_propagates_after_indicator_stops():
    console = _FakeConsole(is_terminal=True)

    def boom():
        raise ValueError("network down")

    try:
        run_with_indicator(console, "msg", boom)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError to propagate")

    assert console.calls == [("enter", "msg", "dots"), ("exit", "msg", "dots")]


def test_args_and_kwargs_are_forwarded():
    console = _FakeConsole(is_terminal=True)
    received = {}

    def func(a, b, kw=None):
        received["args"] = (a, b)
        received["kw"] = kw
        return "ok"

    result = run_with_indicator(console, "msg", func, 1, 2, kw="x")
    assert result == "ok"
    assert received == {"args": (1, 2), "kw": "x"}
