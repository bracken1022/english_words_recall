# Contract: State-Driven Rendering & Feedback Presentation

Implemented by `src/web/static/app.js` and `templates/index.html`. Covers
FR-001 through FR-006. Extends (does not replace)
`specs/003-web-ui/contracts/loading-indicator-contract.md` and
`responsive-layout-contract.md`, which still govern the spinner's timing
and the page's breakpoints respectively.

## Single-primary-area rule (FR-001)

At any moment, exactly one of the following is the page's primary
interactive area, driven directly by `GET /api/state`'s `step` field —
never zero, never more than one:

| `step` | Primary area shown |
|---|---|
| `"empty"` | The "no items available" message |
| `"recall"` | The vocabulary question + answer input |
| `"sentence"` | The sentence-practice prompt + input (word feedback, see below, is shown alongside this, not instead of it) |
| `"feedback"` | The review result + Continue control (word feedback also still shown alongside this) |
| `"complete"` | The "session complete" message |

This is the same `showOnly(step)` mechanism `003-web-ui` already
implements for the five `<section>` elements; this feature does not change
that mechanism, only what else (the persistent word-feedback element,
below) is shown independently of it.

## Persistent word-feedback element (FR-002, FR-003)

- A word-feedback element exists **outside** the five per-step
  `<section>`s (not hidden by `showOnly()`).
- It is shown, populated from `GET /api/state`'s `answer`/`correct` fields
  (`contracts/web-api-contract-delta.md`), whenever `step` is `"sentence"`
  or `"feedback"` — and hidden for every other `step`.
- Because it is rendered from `GET /api/state` on every load (not only from
  the transient `POST /api/answer` response), it is present identically
  whether the learner just submitted the answer in this session or the
  page was just reloaded mid-sentence-step.

## Word-feedback content rule (FR-005, FR-006)

- When `correct` is `true`: text reads `Correct: <accepted_expressions
  joined with ", ">`, styled with the `.feedback-correct` class (a
  distinct, legible color — e.g., green).
- When `correct` is `false`: text reads `Incorrect. The correct expression
  is: <accepted_expressions joined with ", ">`, styled with the
  `.feedback-incorrect` class (a distinct, legible color — e.g., red).
- The class controls color only; the text above is always present
  regardless of styling support, so the result is never conveyed by color
  alone.

## Input/button grouping rule (FR-004)

- Every `<input>` that has a corresponding submit `<button>` (the
  vocabulary-answer form and the sentence form) is wrapped, together with
  that button, in a `.field-row` container using a row flex layout — the
  button is always immediately adjacent to its input, at every viewport
  width already covered by `responsive-layout-contract.md`.

## Duplicate-submission prevention, client side (FR-007, FR-008)

- The sentence form's input and submit button are both set `disabled` the
  instant its `fetch("/api/sentence")` call is issued, and re-enabled once
  that call settles (success or failure) — see
  `web-api-contract-delta.md` for the server-side half of this guarantee.

## Out of scope for this contract

- The spinner's own timing (still governed entirely by `003`'s
  `loading-indicator-contract.md` — unchanged by this feature).
- Exact color values / hex codes — any legible green/red pairing satisfies
  FR-006; none is mandated.
