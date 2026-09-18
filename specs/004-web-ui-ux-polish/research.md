# Phase 0 Research: Web UI State & Feedback Polish

Each decision below is grounded in re-reading `003-web-ui`'s actual current
code (`src/web/templates/index.html`, `static/{style.css,app.js}`,
`session_state.py`) against this feature's five requirements — not written
from a blank slate.

## Input/button grouping (FR-004)

- **Decision**: Wrap each `<label>+<input>+<button>` triple in a
  `.field-row` flex container (`display: flex; gap: 8px`) with the input
  set to `flex: 1` instead of `width: 100%`, so the button sits immediately
  beside the input rather than being pushed to its own line below a
  full-width input.
- **Rationale**: Confirmed the actual bug: `style.css`'s
  `input[type="text"] { width: 100%; }` inside a `section { flex-direction:
  column }` forces the input to fill the column, leaving the button no
  room except a new line below — exactly "awkwardly detached." A row
  flex container is the minimal fix; the mobile-first/responsive rules from
  `003-web-ui`'s `responsive-layout-contract.md` are otherwise untouched
  (a `.field-row` still fits within the existing single-column, no-overflow
  layout at every width already tested there).
- **Alternatives considered**: A CSS grid with fixed input/button track
  sizes — rejected as more machinery than a two-item row needs; a flex row
  does the same job with less code.

## Word-feedback color + wording (FR-005, FR-006)

- **Decision**: Add `.feedback-correct { color: <green> }` and
  `.feedback-incorrect { color: <red> }` classes, toggled in JS based on
  the `correct` boolean already available; update the displayed text to
  `Correct: <expressions>` / `Incorrect. The correct expression is:
  <expressions>` (joining multiple accepted expressions with ", " when an
  item has alternates — the spec's example shows one word, but doesn't
  forbid an item with alternates from listing more than one; the *form*
  — explicit text plus color — is what's required, per spec.md
  Assumptions).
- **Rationale**: Confirmed the actual gap: `recallResultEl` today has no
  color styling at all, and its text reads "Correct! Accepted
  expression(s): …" — present, but not the requested wording, and with no
  color signal. Both are direct, literal requirements (FR-005/FR-006), not
  design choices to weigh alternatives on.
- **Alternatives considered**: Using an icon (✓/✗) instead of, or in
  addition to, color — not requested and not necessary: the spec is
  explicit that *text* is the non-color signal that must always be present;
  an icon would be an unrequested addition, not a requirement.

## Word feedback must survive the transition to the sentence step (FR-002, FR-003 — Acceptance Scenario 2)

- **Decision**: Two changes together:
  1. Move the word-feedback element out of `#recall-view` into its own
     persistent block, rendered whenever the current step is `"sentence"`
     or `"feedback"` (not tied to whichever `<section>` is currently the
     "primary" one per FR-001).
  2. Extend `PracticeSession.state()` (`src/web/session_state.py`) to
     include `answer` and `correct` for the `"sentence"` and `"feedback"`
     steps, sourced from the already-existing `pending_attempt` dict — no
     new computation, just exposing two fields that are already being
     tracked server-side but never returned by `GET /api/state` today.
- **Rationale**: Confirmed the actual bug: `showOnly(step)` sets `hidden =
  true` on every section except the current one, and the word-feedback
  paragraph lives inside `#recall-view` — so the instant the step advances
  to `"sentence"`, the word feedback is hidden along with it, even though
  Acceptance Scenario 2 requires both visible together. Relying only on
  the transient `POST /api/answer` response (as today's JS does) would
  make this work for a live, uninterrupted session but silently break on
  a page reload mid-sentence-step, since the reload's `GET /api/state`
  wouldn't carry the recall outcome at all. Exposing the two fields that
  already exist in `pending_attempt` is the smallest change that makes
  `GET /api/state` a true, complete source of truth for what to render —
  which is exactly what FR-001 ("render according to the current learning
  state") requires of it.
- **Alternatives considered**: Keeping word feedback client-side-only
  (JS variable set at answer-submit time, never persisted server-side) —
  rejected: works for the live-session path but leaves `GET /api/state`
  incomplete, which is inconsistent with treating it as the single source
  of truth, and would silently regress on reload (untested, easy to miss).
  Storing the feedback text itself (not just `answer`/`correct`) — rejected
  as unnecessary: the client already knows how to format "Correct: X" from
  `correct` + `accepted_expressions` (already returned), so no new
  formatted-string field is needed.

## Duplicate sentence-submission guard (FR-007, FR-008)

- **Decision**: Two layers, not one:
  1. **Client**: disable the sentence input and submit button for the
     duration of the `fetch("/api/sentence")` call (re-enabled in that
     call's `finally`, harmless even when the step has since advanced and
     the whole section is about to be hidden anyway).
  2. **Server**: add a `_review_in_progress` guard flag to
     `PracticeSession`. `submit_sentence` sets it before calling
     `request_correction` and clears it in a `finally`; a second call made
     while the flag is set raises `WrongStepError` (`409`, same as any
     other wrong-step request) without starting a second review.
- **Rationale**: Confirmed the actual gap: nothing today disables the
  sentence form, and — more importantly — `PracticeSession.step` doesn't
  advance to `"feedback"` until *after* the (blocking, multi-second)
  `request_correction` call returns, so the existing `step != "sentence"`
  check does **nothing** to stop a second `POST /api/sentence` sent while
  the first is still outstanding; it would start a second, concurrent
  review for the same item. The client-side disable handles the normal
  case (one person, one browser, one click), but `003-web-ui`'s own
  Assumptions already flag that this is a single *shared* session reachable
  from multiple devices — so a second request could plausibly arrive from
  a different tab or device while the first is in flight, which only a
  server-side guard actually prevents. FR-008's wording ("the system MUST
  prevent...") reads as a real guarantee, not just a UI nicety, so both
  layers are in scope.
- **Alternatives considered**: Server-side guard only (skip disabling the
  control) — rejected: would let a learner's own double-click show a
  visibly broken UI (second click does nothing with no feedback) even
  though the request is safely rejected underneath; the client-side
  disable is what makes that rejection invisible/expected rather than a
  silent no-op. Client-side guard only — rejected per the concurrency gap
  above: it does not actually prevent a second request from a second tab
  or device, only from clicking twice in the same one.

## Testing the duplicate-submission guard without real concurrency

- **Decision**: Test the server-side guard directly and deterministically:
  call `PracticeSession.submit_sentence(...)` with a `correction_fn` that,
  from *inside* itself, calls `submit_sentence` again before returning
  (simulating "a second request arrives while the first is still running")
  and asserts the inner call raises `WrongStepError`. This proves the guard
  works without needing real threads, a slow mock, or timing-dependent
  test code.
- **Rationale**: This is the standard way to test a reentrancy guard: make
  the guarded call re-enter itself synchronously. It's deterministic (no
  flakiness from real timing) and tests the actual mechanism (the flag
  being set before the correction call and cleared after), not a proxy for
  it.
- **Alternatives considered**: Spinning up real threads and using a
  `time.sleep` in a mocked `correction_fn` to create a real race — rejected
  as flaky-by-construction (timing-dependent) for no additional confidence
  over the deterministic re-entrant version above.
