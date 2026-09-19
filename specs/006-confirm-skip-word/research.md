# Research: Confirm Before Skipping a Word Without a Sentence

No open `NEEDS CLARIFICATION` markers remained in spec.md's Technical
Context — the codebase already had enough established precedent to resolve
every design question below without new external research. This file
records the decisions and the alternatives considered.

## 1. How to show the confirmation prompt

**Decision**: Use the browser's native `window.confirm()` dialog, invoked
from `app.js`'s existing sentence-form submit handler, before any network
request is made.

**Rationale**: spec.md's Assumptions explicitly leave the prompt's visual
treatment as an implementation choice — what matters is that it clearly
asks for confirmation before skipping. `confirm()` is synchronous, requires
no new markup, no new CSS, and no state management (the dialog itself
*is* the state while it's open). It is also trivial to test in Playwright
or any browser-automation tool via `page.on('dialog', ...)`, and trivial to
reason about for a single-learner local tool where dialog styling
consistency is a minor concern compared to shipping the actual capability.

**Alternatives considered**:
- **Custom in-page modal styled to match the notebook/card redesign**
  (`005`'s stamp/paper aesthetic). Rejected for now: meaningfully more
  code (markup, CSS, focus-trapping, escape-key handling) for a
  confirmation that only needs to communicate "you didn't write anything —
  skip this word?" Revisit later if the native dialog's visual
  inconsistency bothers the learner in practice; nothing in this feature's
  contract locks in `confirm()` specifically, only "a confirmation before
  skipping."
- **No confirmation, just skip silently on empty submit**. Rejected —
  contradicts the explicit ask ("pop up a message to confirm").
- **Disable the submit button until text is entered (no skip at all)**.
  Rejected — removes the actual capability being requested (a way to move
  on without writing a sentence).

## 2. Where the "is this empty" check happens

**Decision**: Client-side, in `app.js`, on the sentence form's `submit`
handler — `sentenceInput.value.trim() === ""` — before any `fetch` call.

**Rationale**: Matches FR-003 ("MUST NOT send an empty or whitespace-only
sentence for correction") most directly: if the check happened server-side
instead, an empty sentence would still need to travel to the server first,
and the confirmation would need a round trip before the learner sees it.
Checking client-side means zero network activity happens until the
learner has already confirmed intent, which is both simpler and strictly
faster.

**Alternatives considered**:
- **Server-side check inside `POST /api/sentence`, returning a "confirm?"
  sentinel response**. Rejected — turns one simple confirm/skip flow into
  a two-request protocol for no benefit, and still requires the same
  client-side `confirm()` call to actually show anything to the learner.

## 3. New state-machine transition

**Decision**: Add `PracticeSession.skip_sentence()`, valid only when
`step == "sentence"` (else raises `WrongStepError`, matching every other
transition method's convention). On success it: appends a `PracticeAttempt`
with `sentence=None`/`feedback=None` to the progress log, updates
`correct_count` from the already-known recall outcome, and advances
`current_index`/`step` exactly the way `continue_to_next()` does — except
it goes directly from `"sentence"` to `"recall"`/`"complete"`, never
visiting `"feedback"`.

**Rationale**: `continue_to_next()` cannot be reused as-is because it
requires `step == "feedback"` and reads `self.last_correction` (which
doesn't exist for a skipped word). The two methods share the
"finalize this attempt, advance the index, compute the new step" shape,
but a skip has one less step to pass through and no correction result to
discard. Keeping them as separate methods matches the existing pattern of
one method per explicit transition (`submit_answer`, `submit_sentence`,
`continue_to_next`) rather than adding conditional branches to an existing
method for a materially different path.

**Alternatives considered**:
- **Reuse `submit_sentence("")` and special-case empty input server-side
  to skip correction**. Rejected — would still pass through `"feedback"`
  (contradicts FR-004: "without ... showing sentence-correction feedback
  for the skipped word"), and conflates two different learner intents
  ("I wrote nothing, treat it as a real empty answer" vs. "I want to skip")
  under one endpoint.

## 4. `PracticeAttempt` / progress-log shape for a skipped word

**Decision**: No changes. `PracticeAttempt` already allows
`sentence=None`/`feedback=None` (both must be present or both absent —
see `src/models/practice_attempt.py`), and `progress_log.append_attempt`
already omits the `sentence:`/`feedback:` YAML keys entirely when
`sentence is None`. A skipped attempt is therefore already
distinguishable from a completed one (FR-007) purely by the *absence* of
those two keys in its logged block — no new field, flag, or format change
needed.

**Rationale**: This exact shape has existed in the data model since
`001-vocab-recall-tutor` (the CLI's `run_recall_step` even constructs an
intermediate `PracticeAttempt` with no sentence before the sentence step
runs) — it was simply never *persisted* in that shape before, because
every existing code path always went on to fill in a sentence before
calling `append_attempt`. This feature is the first to persist that
already-valid shape as a final record rather than an intermediate one.

**Alternatives considered**:
- **Add an explicit `skipped: true` field**. Rejected — redundant with the
  existing absence-of-sentence signal, and would require a
  `PracticeAttempt`/format change plus a migration note, for no new
  information.

## 5. Test strategy

**Decision**: Follow the three existing tiers exactly as `003`/`004` did:
- `tests/unit/test_session_state.py` — `skip_sentence()` transition
  correctness (wrong-step rejection, index/step advancement, correct_count
  bookkeeping, last item → `"complete"`).
- `tests/contract/test_web_api_contract.py` — `POST /api/skip` HTTP-level
  behavior (200 + new state shape when valid, 409 + no state change when
  not, and — importantly — that `request_correction` is never invoked for
  this path, via `unittest.mock.patch` the same way existing sentence
  tests already patch it).
- `tests/integration/test_web_session_flow.py` — one full
  recall → skip → (next word or complete) scenario through the real Flask
  test client, plus a read-back of the progress file confirming the
  skipped entry has no `sentence`/`feedback` keys.
- `tests/unit/test_web_static_assets.py` — a static-content assertion that
  `app.js` contains the empty-check/confirm/`/api/skip` wiring, matching
  the project's established "no JS test runner" convention rather than
  introducing one.

**Alternatives considered**:
- **Add Playwright (or similar) as a real browser-test dependency**.
  Rejected for this feature — it would be the first browser-automation
  dependency added to the project's checked-in test suite, a meaningfully
  larger scope decision than what was asked for, and the existing
  static-assertion + manual `quickstart.md` convention already covers
  every other piece of frontend behavior in this codebase (spinner,
  hidden-attribute handling, word-feedback wording, etc.). Revisit only if
  the project decides more broadly to adopt browser testing.
