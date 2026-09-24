# Research: Choose Sequential or Random Word Order

No open `NEEDS CLARIFICATION` markers — the one real fork (CLI+web vs.
web-only scope) was already resolved in spec.md's Clarifications session
before planning began. This file records the remaining implementation-shape
decisions and the alternatives considered.

## 1. Where shuffling happens

**Decision**: `random.shuffle(self.items)` (in-place, stdlib) called
exactly once, immediately after `self.items` is finalized by filtering:
- In `PracticeSession.__init__()`'s existing "locked" branch (used when
  `group_locked` is `True` — a pre-selected group, or no interactive
  choice offered at all), right after the existing
  `if group is not None: items = [...]` filter.
- In `select_collection()` (the interactive web path), right after the
  existing `key`-based filter, before `current_index`/counters are reset.
- In the CLI's `run_session()`, right after its own existing
  `if group is not None: items = [...]` filter.

**Rationale**: Every one of these three sites already has the exact
moment "the pool for this session is now final" — shuffling there, once,
keeps the change minimal (one line added at each of three already-existing
filter points) and guarantees FR-003 ("decided once... MUST NOT change
partway through") for free, since nothing after that point ever touches
list order again.

**Alternatives considered**:
- **Shuffle lazily, e.g. by randomizing `current_index`'s next-item
  lookup** — rejected: needlessly reinvents what a single upfront shuffle
  already guarantees, and would make "every word exactly once" (FR-002)
  harder to reason about than it needs to be.

## 2. API shape: one parameter, threaded through existing entry points

**Decision**: A single `order: str = "sequential"` parameter added to
`PracticeSession.__init__`, `PracticeSession.select_collection`,
`run_session` (CLI), and `create_app` (web) — accepting exactly
`"sequential"` or `"random"`. Any other value (not reachable through
either real UI) is treated the same as `"sequential"` — no shuffle,
matching how an unrecognized `select_collection` key already degrades to
an empty pool defensively rather than raising (spec `007` research.md
§4) — the same "defensive, never-crashing" posture applied here.

**Rationale**: Defaulting to `"sequential"` everywhere means every
existing call site in the codebase (and every existing test) that doesn't
pass `order` keeps today's exact behavior with zero changes required —
this is what makes FR-003/SC-003 ("indistinguishable from today") true
by construction rather than by extra effort.

**Alternatives considered**:
- **A boolean `random_order: bool = False`** — rejected: the spec and
  this feature's own naming throughout is "sequential order" / "random
  order" as two named choices, not a yes/no flag; a string with two valid
  values reads more clearly at every call site (`order="random"` vs.
  `random_order=True`) and leaves room for a third option later without
  a breaking rename, though none is planned now.

## 3. CLI `--order` flag; web `--order`'s narrower scope

**Decision**: Both `src/cli/__main__.py` and `src/web/__main__.py` get an
`--order` flag: `argparse.add_argument("--order", choices=["sequential",
"random"], default="sequential")`. For the CLI, this always takes effect
directly (the CLI has no interactive picker of any kind — Assumptions).
For the web UI, `--order` only takes effect when `--group` is *also*
given — i.e., only in `group_locked` mode. When no `--group` is given,
`create_app` passes `offer_choice=True` (existing spec `007` behavior)
and the interactive choose screen always governs order fresh, the same
way it already governs collection choice regardless of any startup
default.

**Rationale**: This mirrors `--group`'s own existing behavior exactly:
today, `--group` given ⇒ locked, no picker; `--group` omitted ⇒ picker
governs, and no "default group" startup flag exists to partially
pre-fill that picker either. Making `--order` follow the identical rule
(only meaningful in locked mode) keeps the mental model uniform — "startup
flags fully configure a locked session, or you get the fully interactive
picker for both choices together" — rather than a partially-mixed mode
where one choice is pre-set and the other isn't.

**Alternatives considered**:
- **Let `--order` pre-select a default on the interactive picker even
  without `--group`** — rejected as unnecessary scope: spec.md FR-005 only
  requires *both* an interactive and a non-interactive path to exist, not
  that they interoperate; adding a "pre-filled but still changeable"
  middle state is complexity the spec never asked for.

## 4. Web UI: one combined choose screen, not two

**Decision**: The existing `#choose-view` (spec `007`) gains an order
toggle (two options, always visible, defaulting to "Sequential"
selected) above or alongside the collection list. Clicking a collection
button sends `POST /api/select` with both `{"collection": <key>, "order":
<"sequential"|"random">}` in one request — not two separate steps.

**Rationale**: Spec.md's Assumptions are explicit about this: "one
combined 'how do you want to practice' choice instead of two." Since the
two settings are otherwise independent, sending them together in the
single existing action (picking a collection) that already finalizes the
pool avoids inventing a new screen, a new state-machine step, or a
two-request sequence with its own new failure modes.

**Alternatives considered**:
- **A second screen/step for order, after collection choice** — rejected
  per spec.md's explicit Assumption against a second screen.
- **Two separate `POST` calls (order first, then collection)** — rejected:
  adds an intermediate, storable-but-pointless "order chosen, collection
  not yet" state with no test or user value over one combined request.

## 5. Request contract: `order` is optional, unlike `collection`

**Decision**: In `POST /api/select`'s request body, `"order"` is
**optional** — if omitted (or not one of the two valid strings), the
server treats it as `"sequential"`. This differs from `"collection"`,
which remains **required** (missing it is still a `400`, unchanged from
spec `007`).

**Rationale**: `"collection"`'s required-ness exists because `null` is
itself a meaningful, intentional value (practice everything) distinct
from "the learner didn't choose anything yet" — the `400` on a missing
key is what lets the server tell those two apart. `"order"` has no such
ambiguity: there is exactly one sensible default (`"sequential"`, matching
today's untouched behavior), so a client that doesn't send it at all gets
the same safe, expected result as a client that explicitly sends
`"sequential"`. Requiring it would only add a new class of `400`s for no
benefit.

**Alternatives considered**:
- **Require `order` just like `collection`, for symmetry** — rejected:
  symmetry with `collection` isn't a goal in its own right, and this
  would break the "existing behavior when nothing new is sent" property
  this feature is otherwise designed to preserve automatically.

## 6. Test strategy

**Decision**: Same tiers as `006`–`010`:
- `tests/unit/test_session_state.py` — `order` on `__init__`/
  `select_collection`, verified by patching `random.shuffle` (asserting
  it's called only for `"random"`) and by asserting the resulting
  `self.items` is always a permutation of the same items regardless of
  order (`sorted(...) == sorted(...)`).
- `tests/integration/test_session_order.py` (**new**, mirroring
  `test_session_group_filter.py`'s style) — `run_session(order=...)`
  through the same `builtins.input`-monkeypatched flow already used for
  CLI integration tests.
- `tests/contract/test_web_api_contract.py` — `POST /api/select`'s
  `"order"` field: present/absent/invalid all handled per §5.
- `tests/integration/test_web_session_flow.py` — one full
  choose-with-random-order scenario through the real Flask test client.
- `tests/unit/test_web_static_assets.py` — static assertion that `app.js`
  tracks the selected order and includes it in the `POST /api/select`
  body, matching the established "no JS/browser test runner" convention.

**Alternatives considered**: Asserting actual randomized output order
directly (e.g., running many trials and checking statistical properties)
— rejected: flaky by nature (a fair shuffle can legitimately return the
original order), and unnecessary when "was `random.shuffle` invoked" is a
precise, deterministic, and sufficient thing to assert instead.
