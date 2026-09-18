"""Indeterminate loading indicator for a long-running call (spec 002,
contracts/loading-indicator-contract.md).

Boundary rule: this wrapper is display-only. It calls *func* exactly once
and returns its result unmodified — it never inspects or branches on what
*func* returns, and never changes when/whether *func* is called.
"""

from collections.abc import Callable
from typing import TypeVar

from rich.console import Console

T = TypeVar("T")


def run_with_indicator(
    console: Console,
    message: str,
    func: Callable[..., T],
    *args,
    **kwargs,
) -> T:
    """Show *message* as an indeterminate loading indicator for the duration
    of `func(*args, **kwargs)`, then return its result unchanged.

    On an interactive terminal, shows an animating spinner via
    `console.status()`. On non-interactive output, `console.status()`
    renders nothing at all (verified in research.md), so this instead
    prints `message` once via `console.print()` and does not animate.
    """
    if console.is_terminal:
        with console.status(message, spinner="dots"):
            return func(*args, **kwargs)
    else:
        console.print(message)
        return func(*args, **kwargs)
