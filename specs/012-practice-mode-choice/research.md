# Research: Choose Recall-Only or Sentence Practice Mode

No open `NEEDS CLARIFICATION` markers — the one real fork (CLI+web vs.
web-only scope) was already resolved in spec.md's Clarifications session
before planning began, following spec `011`'s directly applicable
precedent. This file records the remaining implementation-shape
decisions and the alternatives considered.

## 1. `mode` must be stored session state, not a consume-once parameter

**Decision**: Unlike `order` (read once, at the moment the pool is
finalized, then discarded), `mode` is stored as a persistent attribute —
`self.recall_only: bool` — set once at the moment the mode is decided
(`__init__`'s locked branch, or `select_collection()`), and then
consulted by `submit_answer()` on *every* word for the rest of the
session.

**Rationale**: `order` only ever affects the pool's sequence at one
instant (before the walk starts); nothing "order-related" happens on
each subsequent step. `mode`, by contrast, changes what `submit_answer()`
itself does on every single call, for as long as the session runs. A
consume-once parameter can't express that; it has to become session
state.

**Alternatives considered**:
- **Re-derive the mode from something else each time** (e.g., store the
  raw `"sentence"`/`"recall-only"` string instead of a bool) — rejected:
  a bare bool (`self.recall_only`) is simpler to branch on at every call
  site than re-comparing a string each time, and nothing else needs the
  original string once it's been resolved.

## 2. Where `submit_answer()` branches, and reusing the existing finalization tail

**Decision**: `submit_answer()` grades the answer exactly as it does
today, then branches:
- **Sentence mode** (`self.recall_only is False`, default): unchanged —
  stash `pending_attempt`, move to `"sentence"`.
- **Recall-only mode**: skip `"sentence"` entirely. Immediately build the
  `PracticeAttempt` (no `sentence`/`feedback` fields), `append_attempt()`
  it, tally `correct_count` if correct, advance `current_index`, and land
  on `"complete"` or `"recall"` — the exact same four-step tail
  `skip_sentence()` and `continue_to_next()` already both perform.

**Rationale**: This tail already exists, twice, doing precisely what
FR-002/FR-006 need (finalize an attempt without a sentence, tally it,
advance). Reusing it a third time, inline in `submit_answer()`, is
strictly less code than introducing a fourth "mode" concept into the
state machine's step names — no new step is introduced; a recall-only
session only ever visits `"recall"` and `"complete"`, never `"sentence"`
or `"feedback"` at all.

**Alternatives considered**:
- **Still visit `"sentence"`, but auto-skip it** (i.e., route through the
  existing `skip_sentence()` action automatically) — rejected: this
  would still require the client to display a sentence prompt for one
  frame, or would require `submit_answer()` to internally call
  `skip_sentence()` right after setting `self.step = "sentence"`, which
  is more convoluted than simply never entering that step. It would also
  make `GET /api/state` racy for a client between the two calls if they
  were ever split into separate requests.
- **Extract the shared tail into a private helper method** — considered
  and likely worth doing during implementation (three call sites is the
  established "rule of three" threshold), but this is an internal
  refactor with no externally observable difference; left as an
  implementation-time judgment call rather than a researched decision.

## 3. API shape: one parameter, threaded through existing entry points

**Decision**: A single `mode: str = "sentence"` parameter added to
`PracticeSession.__init__`, `PracticeSession.select_collection`,
`run_session` (CLI), and `create_app` (web) — accepting exactly
`"sentence"` or `"recall-only"`. Any other value (not reachable through
either real UI) is treated the same as `"sentence"` — the same
defensive-default posture `order` already established (research.md §2 in
spec `011`).

**Rationale**: Mirrors `order`'s already-proven shape exactly, so the
same "every existing call site that doesn't pass `mode` keeps today's
exact behavior" property holds by construction (FR-005, SC-003).

**Alternatives considered**:
- **A boolean `recall_only: bool = False` at the public API boundary
  too** — rejected: the spec's own vocabulary is "sentence mode" /
  "recall-only mode" as two named choices (matching how it already
  describes "sequential"/"random" for order), so the public parameter
  stays a two-valued string for consistency with `order`, even though it
  collapses to a bool (`self.recall_only`) internally once resolved.

## 4. CLI `--mode` flag; web `--mode`'s narrower scope

**Decision**: Both `src/cli/__main__.py` and `src/web/__main__.py` get a
`--mode` flag: `argparse.add_argument("--mode", choices=["sentence",
"recall-only"], default="sentence")`. For the CLi, this always takes
effect directly. For the web UI, `--mode` only takes effect when
`--group` is *also* given (`group_locked` mode) — exactly the same
narrower-scope rule spec `011` already established for `--order`, for
the same reason: when no `--group` is given, the interactive choose
screen always governs mode fresh, the same way it already governs
collection and order regardless of any startup default.

**Rationale**: Consistency with `order`'s already-shipped, already-tested
rule — one mental model ("startup flags fully configure a locked
session, or you get the fully interactive picker for all three
choices together") rather than a fourth special case.

**Alternatives considered**: None beyond what spec `011`'s research.md
§3 already considered and rejected for the identical fork.

## 5. Web UI: mode joins the existing combined choose screen

**Decision**: The existing `#choose-view` (specs `007`/`011`) gains a
third control — a mode toggle (two options, always visible, defaulting
to "Sentence" selected), alongside the order toggle already there.
Clicking a collection button sends `POST /api/select` with
`{"collection": <key>, "order": <...>, "mode": <"sentence"|"recall-only">}`
in one request — not a separate step.

**Rationale**: Spec.md's Assumptions are explicit: "one combined choice
covering collection, order, and mode together, submitted in the same
selection action" — directly extending the precedent spec `011` set for
order, for the same reasons (no new screen, no new state-machine step,
no two-request sequence).

**Alternatives considered**: A separate screen/step for mode — rejected
per spec.md's explicit Assumption, for the same reasons `011`'s
research.md §4 already rejected a separate order screen.

## 6. Request contract: `mode` is optional, unlike `collection`

**Decision**: In `POST /api/select`'s request body, `"mode"` is
**optional** — if omitted (or not one of the two valid strings), the
server treats it as `"sentence"`. This is exactly `order`'s existing
optionality rule (spec `011` research.md §5), applied to the same shape
of setting.

**Rationale**: There is exactly one sensible default (`"sentence"`,
matching today's untouched behavior), so a client that doesn't send
`"mode"` at all gets the same safe, expected result as one that
explicitly sends `"sentence"`. Symmetry with the required `"collection"`
field isn't a goal in its own right (spec `011` research.md §5 already
made this exact case).

## 7. Test strategy

**Decision**: Same tiers as `006`–`011`:
- `tests/unit/test_session_state.py` — `mode`/`self.recall_only` on
  `__init__`/`select_collection()`; `submit_answer()`'s branch verified
  by patching `request_correction`/asserting it's never invoked in
  recall-only mode, asserting `self.step` never becomes `"sentence"`,
  and asserting the tally/progress-log shape matches `skip_sentence()`'s
  existing shape (no `sentence`/`feedback` fields).
- A CLI-level integration test (new module or an addition alongside
  `tests/integration/test_session_group_filter.py`, per tasks.md) —
  `run_session(mode="recall-only")` never calls `request_correction`/
  `run_sentence_step`, and the progress log still records every word.
- `tests/contract/test_web_api_contract.py` — `POST /api/select`'s
  `"mode"` field: present/absent/invalid all handled per §6; a full
  recall-only flow through the test client confirms `POST /api/answer`
  goes straight to `"recall"`/`"complete"`, never `"sentence"`.
- `tests/unit/test_web_static_assets.py` — static assertion that
  `app.js` tracks the selected mode and includes it in the
  `POST /api/select` body, matching the established "no JS/browser test
  runner" convention (the same pattern `011` used for order).

**Alternatives considered**: None beyond what `011`'s research.md §6
already considered for the structurally identical order feature.
