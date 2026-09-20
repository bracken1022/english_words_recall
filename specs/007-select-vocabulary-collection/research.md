# Research: Choose a Vocabulary Collection Before Practicing

No open `NEEDS CLARIFICATION` markers remained in Technical Context — the
one real open question (mid-session switching) was already resolved in
spec.md's Clarifications session before planning began. This file records
the remaining design decisions and the alternatives considered.

## 1. What "collection" maps to in the existing data model

**Decision**: Reuse `VocabularyItem.group` (`str | None`) exactly as it is
today — no changes to `vocabulary_loader.py` or `VocabularyItem`.

**Rationale**: Already decided in spec.md's Assumptions: the learner's own
vocabulary folder already tags each file's words with one `group` value,
so reusing it satisfies the feature description's example with zero data-
model change. `--group`-based filtering (`items = [i for i in items if
i.group == group]`) already exists and is already exercised by
`session_state.py`, `src/cli/__main__.py`, and `src/web/__main__.py` — this
feature only adds a way to make that same choice *interactively*, at
runtime, instead of only via a startup flag.

**Alternatives considered**: A true file-level selection (tracking which
`.md` file each item came from) — rejected as unnecessary scope: it would
require `vocabulary_loader.load_vocabulary` to start returning per-item
provenance, a real (if small) data-model change, for no behavioral
difference given the learner's actual vocabulary folder today.

## 2. Representing "practice everything" and "ungrouped" on the wire

**Decision**: One `collections` list in `GET /api/state` (step `"choose"`),
each entry `{"key": ..., "label": ..., "count": ...}`:
- `{"key": null, "label": "Practice everything", "count": <all items>}` —
  always first.
- One entry per distinct `group` value found, alphabetically by key.
- `{"key": "__ungrouped__", "label": "Ungrouped words", "count": ...}` —
  last, only present if at least one loaded item has `group is None`.

`POST /api/select` takes `{"collection": <key>}`, using the same three
shapes (`null`, a real group string, or the `"__ungrouped__"` sentinel).

**Rationale**: `null` already means "no filter" everywhere in this
codebase (`group: str | None = None`) — reusing it for "practice
everything" needs no new convention. A distinct sentinel string is needed
for "ungrouped" specifically because `None` is already taken by "practice
everything"; `"__ungrouped__"` is reserved for this purpose only,
analogous to how the codebase already accepts a single flat namespace of
group strings. Collision with a real learner-authored group literally
named `__ungrouped__` is theoretically possible but not realistically a
concern for a single-learner local tool with no adversarial input —
documented here rather than defended against, matching this project's
existing risk posture (e.g., no input sanitization is done anywhere else
in this codebase either, for the same reason).

**Alternatives considered**: Two separate top-level fields (`collections`
+ a boolean/flag for "practice everything") — rejected as needless API
surface; one list keeps `POST /api/select`'s contract to a single shape
regardless of which kind of choice was made.

## 3. Where "choose" sits in the state machine, and startup-flag compatibility

**Correction made during implementation**: nearly the entire existing test
suite constructs `PracticeSession`/`create_app` without passing `group` at
all, relying on today's default (`group=None` → immediate, unfiltered
`"recall"`). Deriving `group_locked` from `group is not None` alone (as
first drafted) would have silently turned every one of those into the new
`"choose"` step, breaking dozens of pre-existing, unrelated tests. Fixed
by adding an explicit opt-in constructor parameter, `offer_choice: bool =
False` (and the same parameter on `create_app()`), so the new step only
ever activates when a caller *asks* for it. `group_locked` is derived as
`not (offer_choice and group is None)`.

**Decision**: `PracticeSession` gains a `group_locked: bool` field,
derived from the new `offer_choice` parameter (see above and
`data-model.md`). When `group_locked` is `True`, behavior is **exactly**
today's: filter immediately, start in `"recall"`/`"empty"`, and
`"complete"` stays a dead end (`continue_to_next()` on `"complete"`
remains a no-op, unchanged). When `group_locked` is `False` (the new
default — no `--group` given), `__init__` stores the *full* loaded pool
(`self.all_items`) unfiltered, and starts in `"choose"` (or `"empty"` if
there are zero items at all — FR-005). From `"choose"`,
`select_collection(key)` filters `self.all_items` into the active
`self.items` and proceeds into `"recall"`/`"empty"` exactly like `__init__`
does today. From `"complete"` (only when not `group_locked`), a new
`restart()` method re-loads vocabulary from disk and returns to
`"choose"`.

**Rationale**: This keeps the existing `--group`-locked path byte-for-byte
unchanged (SC-004: "existing unattended/scripted startup ... continues to
work exactly as before"), while giving the new interactive path its own
clean, separately-testable entry/exit points — the same pattern `006`
used for `skip_sentence()` (a new method for a new transition, rather than
branching inside an existing one).

**Why `restart()` reloads from disk**: spec.md's Assumptions say vocabulary
changes made "while a session is already running are not picked up until
a new session is started from the choice screen" — reaching `"choose"`
again via `restart()` *is* that moment. Reloading is cheap (small
Markdown files) and requires no new plumbing beyond storing `vocab_dir` on
the session (not currently stored — `__init__` takes it as a parameter but
discards it after the initial `load_vocabulary` call).

**Alternatives considered**:
- **Keep the pool fixed for the process lifetime, only re-filtering
  in-memory on restart** — rejected: contradicts the Assumption's explicit
  wording above, and reloading costs nothing meaningful at this scale.
- **Let `continue_to_next()` itself transition `"complete"` → `"choose"`**
  — rejected: would change `POST /api/continue`'s existing contract
  (currently a documented no-op on `"complete"`), risking exactly the kind
  of accidental behavior change SC-004 rules out. A separate
  `POST /api/restart` endpoint is strictly additive instead.

## 4. Order and defensiveness of collection filtering

**Decision**: Filtering by a chosen key preserves the existing item order
(the same `[item for item in items if <predicate>]` shape already used for
`--group`) — no new sorting of *words*, only of the *collection list*
itself (alphabetical by key, with "practice everything" pinned first and
"ungrouped" pinned last, per §2). If `POST /api/select` is ever sent a key
that matches nothing (not reachable through the real UI, since the UI only
ever sends keys it just received from `GET /api/state`), the resulting
empty item list simply routes to `"empty"` — no crash, no special-cased
recovery, consistent with how `"empty"` already behaves today for a
`--group` value that matches nothing.

**Rationale**: Reuses proven, already-tested filtering logic; avoids
inventing new list-ordering rules the spec never asked for.

## 5. Test strategy

**Decision**: Same three tiers as `003`–`006`:
- `tests/unit/test_session_state.py` — collection-listing shape (practice-
  everything always first, ungrouped only when applicable, counts
  correct), `select_collection()` transition/reset behavior (fresh
  `current_index`/`correct_count`/`pending_attempt`), `restart()`
  transition and its disk-reload, and that `group_locked` sessions never
  expose `"choose"` at all.
- `tests/contract/test_web_api_contract.py` — `POST /api/select` and
  `POST /api/restart` HTTP-level behavior (200/409/400 per
  `contracts/web-api-contract-delta.md`).
- `tests/integration/test_web_session_flow.py` — one full
  choose → recall → ... → complete → restart → choose scenario through the
  real Flask test client, plus one confirming a `--group`-started app
  never shows `"choose"`.
- `tests/unit/test_web_static_assets.py` — static-content assertion that
  `app.js` renders the choose-view from `state.collections` and wires a
  restart control, matching the established "no JS test runner"
  convention (no new browser-test dependency, per `006`'s precedent).
