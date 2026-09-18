# Contract: Browser Loading Indicator (Sentence Review)

Implemented by `src/web/static/app.js`, scoped to the `POST /api/sentence`
call defined in `contracts/web-api-contract.md`. Covers FR-007, SC-004 — the
browser-side counterpart to `002-sentence-review-indicator`'s CLI contract;
the mechanism differs (no terminal/`rich` in a browser) but the behavioral
contract is the same one already established and tested there.

## Timing contract

1. The spinner element MUST become visible in the same synchronous step
   that issues the `fetch()` call to `POST /api/sentence` — before
   awaiting its response, never after.
2. The spinner MUST remain visible, continuously animating (via CSS, not
   JS-computed frames), for the entire time the `fetch()` promise is
   pending — its visible duration is driven entirely by how long the
   actual request takes, never by a fixed or guessed delay (mirrors
   `002`'s FR-002).
3. The spinner MUST be hidden in the `fetch()`'s completion handling —
   covering **both** a normal JSON response (any `available` value) and a
   network-level failure (e.g., the server process itself is unreachable)
   — before the corresponding result or error message is rendered.
4. The spinner MUST NOT display a percentage, a step count, or any other
   specific-progress value (FR-007) — a fixed label (e.g., "Reviewing your
   sentence…") plus a CSS animation are the only content.
5. No minimum or maximum display duration is enforced — a fast response
   clears the spinner immediately, matching `002`'s "no artificial delay"
   finding.

## Display contract

- The spinner is a single DOM element, hidden by default (e.g., via a CSS
  class), shown by adding/removing that class around the `fetch()` call —
  no separate "percentage" or "step" sub-element exists to accidentally
  populate.
- Only the `/api/sentence` call shows this indicator. `/api/answer` and
  `/api/continue` are fast, local, non-LLM calls (per `plan.md`
  Performance Goals) and do not show it, matching `002`'s finding that only
  the LLM-backed call needs one.

## Out of scope for this contract

- The exact CSS animation used for the spinner (any indeterminate,
  continuously-moving visual satisfies FR-007 — no specific animation is
  mandated).
- Server-side timing — that is `POST /api/sentence`'s concern
  (`contracts/web-api-contract.md`), not this one's.
