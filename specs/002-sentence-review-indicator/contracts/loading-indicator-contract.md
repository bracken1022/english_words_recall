# Contract: Loading Indicator Timing

Implemented by `src/cli/loading_indicator.run_with_indicator(console, message,
func, *args, **kwargs)`. This is a UI-behavior contract (no network or file
format involved), covering spec FR-001 through FR-007.

## Signature contract

```python
def run_with_indicator(console: Console, message: str, func: Callable[..., T], *args, **kwargs) -> T:
    ...
```

- Calls `func(*args, **kwargs)` **exactly once**.
- Returns exactly what `func` returned, unmodified — this function MUST NOT
  inspect, transform, or branch on the return value (FR-006: sentence-review
  logic is unchanged; this wrapper is display-only).
- If `func` raises, `run_with_indicator` MUST let the exception propagate
  after stopping the indicator — it MUST NOT swallow or replace it.

## Display-mode contract

| `console.is_terminal` | Behavior |
|---|---|
| `True` | Enter `console.status(message, spinner="dots")` **before** calling `func`; the spinner animates continuously for the entire call; exit the status context (stopping/clearing the spinner) as soon as `func` returns or raises, before `run_with_indicator` returns or re-raises. |
| `False` | Print `message` once via `console.print(message)` **before** calling `func`; do not call `console.status(...)` at all (see `research.md` — it renders nothing when not a terminal); no further output from this function after that one line. |

## Timing contract (maps to FR-001–FR-004)

1. The chosen display (spinner start, or the one plain line) MUST happen
   **before** `func` is invoked — never after, never concurrently in a way
   that could be observed out of order.
2. Nothing about the display MUST depend on how long `func` takes — no
   timers, no minimum/maximum display duration, no artificial delay before
   or after calling `func` (FR-002, and spec Edge Cases: fast completion is
   not a special case).
3. The spinner (terminal case) MUST NOT render a percentage, step count, or
   any other specific-progress value — `spinner="dots"` and a fixed message
   string are the only content shown (FR-004). The non-terminal case's single
   line is likewise a fixed message with no progress value.
4. The indicator MUST be gone (spinner stopped, or nothing further printed
   for the non-terminal case) at the exact point `run_with_indicator` returns
   or raises — the caller (`run_sentence_step`) is guaranteed that by the
   time it prints the correction feedback / unavailable message, no indicator
   output can still appear afterward (FR-003).

## Caller contract (`run_sentence_step`)

`run_sentence_step` MUST call `request_correction(...)` only through
`run_with_indicator(...)` — never directly — and MUST NOT change any of its
existing argument-building, result-branching (needs-correction /
already-correct / missing-expression / unavailable), or progress-log
attachment logic. The only change at the call site is wrapping the existing
call; the four `if/elif` branches already in `run_sentence_step` are
unaffected.

## Out of scope for this contract

- The visual appearance of the spinner itself (frame set, refresh rate) —
  delegated entirely to `rich`, not re-specified here.
- Any change to `contracts/ollama-correction-contract.md`
  (`specs/001-vocab-recall-tutor/contracts/`) — that contract is unmodified;
  this feature only wraps its call site.
