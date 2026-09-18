# Phase 0 Research: Sentence-Review Loading Indicator

## Spinner mechanism: `rich.console.Console.status()`

- **Decision**: Use the existing `rich` dependency's `Console.status(message,
  spinner="dots")` as a context manager around the existing
  `request_correction(...)` call in `run_sentence_step`. On entry it starts
  an indeterminate, continuously animating spinner; on exit (however the
  `with` block exits, including via an exception) it stops and clears the
  spinner automatically.
- **Rationale**: `rich` is already a project dependency (used for the
  existing correct/incorrect coloring), so this adds zero new dependencies.
  `Console.status()` is purpose-built for exactly this case: an
  indeterminate wait with no known progress fraction, which matches FR-004
  directly (there is no percentage to show because none exists). Using a
  context manager also means "stops when the call returns or raises" is
  structural, not something that has to be remembered at every exit point —
  directly satisfying FR-003 for all four outcomes without four separate
  stop calls.
- **Alternatives considered**: `rich.progress.Progress` with an indeterminate
  bar — rejected as heavier machinery for a single indeterminate wait than
  `Console.status()`, which is the simpler, purpose-built API for this exact
  case. A hand-rolled `\r`-overwrite spinner loop on a background thread —
  rejected: reimplements what `rich` already provides correctly, and adds
  real complexity (thread lifecycle, terminal-width edge cases) for no
  benefit over the existing dependency.

## Non-interactive output fallback

- **Decision**: Explicitly check `console.is_terminal` before deciding how
  to show the indicator. When `True`, use `Console.status()` as above. When
  `False`, print one plain line (e.g., "Reviewing your sentence...") and
  proceed — no animation, no `Console.status()` call at all.
- **Rationale**: Verified directly (not assumed): calling
  `Console.status()` on a `Console` whose `is_terminal` is `False` (e.g.,
  output redirected to a file) renders **nothing at all** — not even a
  static line. Confirmed with:

  ```python
  from rich.console import Console
  import io
  c = Console(file=io.StringIO(), force_terminal=False)
  with c.status("Reviewing...", spinner="dots"):
      pass
  c.file.getvalue()  # == '' — completely empty
  ```

  Relying on `rich` to "just handle it" would silently violate FR-001 (the
  learner would see nothing at all, indicator or otherwise) whenever output
  isn't an interactive terminal. The explicit branch is required, not
  optional, to meet FR-007's "must not corrupt output, must still function"
  in a way that also keeps FR-001 satisfied outside a terminal.
- **Alternatives considered**: Always calling `Console.status()` and trusting
  `rich`'s internals — rejected per the measurement above, it produces no
  output in the non-terminal case, which is a spec violation, not a
  graceful degradation. Forcing `force_terminal=True` to make `rich` animate
  even when redirected — rejected: this would emit raw ANSI escape codes
  into a file or pipe, which is exactly the "corrupted output" FR-007 warns
  against.

## Where the wrapper lives

- **Decision**: A small new module, `src/cli/loading_indicator.py`, exposing
  one function: `run_with_indicator(console, message, func, *args, **kwargs)`
  that returns `func(*args, **kwargs)`'s result unchanged, having shown the
  indicator (per the two branches above) for exactly the duration of that
  call — including when `func` raises, since the `with`/`try` structure
  stops the indicator before the exception propagates.
- **Rationale**: Keeping this in `src/cli/` (not `src/services/` or
  `src/lib/`) matches the existing project structure's split: `cli/` is
  presentation/interaction, `services/` is business logic
  (`llm_client.request_correction` stays exactly as it is). A single
  generic wrapper function (rather than inlining the branch into
  `run_sentence_step` directly) makes the timing contract independently
  unit-testable (start called, `func` called exactly once, stop called,
  return value passed through, stop still happens if `func` raises) without
  needing a real or mocked LLM call in that test.
- **Alternatives considered**: Inlining the `if console.is_terminal: ...
  else: ...` branch directly into `run_sentence_step` — rejected: it would
  entangle indicator-timing tests with the full sentence-review flow
  (mocking `request_correction`, asserting printed feedback text, etc.)
  instead of letting the indicator's own contract be tested in isolation,
  and would need to be duplicated if any future call site (e.g., a possible
  future recall-step LLM call) needed the same indicator behavior.

## Testing approach for "the spinner animated"

- **Decision**: Do not attempt to assert on captured ANSI spinner frames.
  Instead, unit-test `run_with_indicator` against a **fake console** object
  exposing `is_terminal` and a `status()` method that records
  enter/exit calls, and integration-test the full `run_sentence_step` flow
  by asserting `run_with_indicator` (or the underlying `console.status`) was
  invoked around the `request_correction` call, plus that the final printed
  feedback is unchanged from `001-vocab-recall-tutor`'s existing behavior.
- **Rationale**: Rendered spinner animation is a terminal-rendering concern
  `rich` itself is already responsible for and already tested by upstream;
  what this feature's own tests need to prove is the *timing contract*
  (starts immediately, spans the call, stops on every outcome, never shows
  a percentage) and the *non-interactive fallback*, both of which are
  fully assertable without a real terminal.
- **Alternatives considered**: Snapshot-testing raw captured stdout bytes
  including ANSI codes — rejected as brittle (coupled to `rich`'s internal
  rendering, terminal width, and spinner frame set) and not what the spec
  actually requires proof of.
