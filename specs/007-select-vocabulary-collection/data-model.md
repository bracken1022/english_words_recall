# Data Model: Choose a Vocabulary Collection Before Practicing

No new persistent entities (spec.md Assumptions: "presentation and
selection only"). This feature adds one new *derived* view over data that
already exists, and extends `PracticeSession`'s in-memory state.

## Derived view: Collection listing (not stored — computed on demand)

Computed from `PracticeSession.all_items` (the full, unfiltered pool)
whenever `state()` is called while `step == "choose"`.

| Field | Type | Notes |
|---|---|---|
| `key` | `string \| null` | `null` = practice everything; a real `group` value; or the reserved sentinel `"__ungrouped__"` |
| `label` | `string` | `"Practice everything"`, the `group` value itself, or `"Ungrouped words"` |
| `count` | `int` | number of items this choice would include, ≥ 1 (an empty collection is never listed) |

Ordering: `null` (practice everything) first, then real `group` values
sorted alphabetically, then `"__ungrouped__"` last (only present if at
least one loaded item has `group is None`).

## `PracticeSession` (existing — `src/web/session_state.py`) — new/changed fields

**Implementation correction (discovered during `/speckit-implement`)**:
`__init__` gains a new parameter `offer_choice: bool = False`, defaulting
to `False` so every existing caller (nearly the entire existing test
suite constructs `PracticeSession`/`create_app` without passing `group`
at all, relying on the *current* default — immediate `"recall"`) keeps
its exact existing behavior unchanged. The new `"choose"` step only
activates when `offer_choice=True` **and** `group is None` — i.e., only
`src/web/__main__.py` sets `offer_choice=args.group is None` when
constructing the real web server; `create_app()` gains and passes through
the same parameter. `group_locked` (below) is derived from both, not from
`group` alone as originally drafted.

| Field | Type | Notes |
|---|---|---|
| `vocab_dir` | `Path` | **new** — stored (previously a constructor parameter, discarded after use) so `restart()` can reload |
| `group_locked` | `bool` | **new** — `not (offer_choice and group is None)`; `True` whenever there's no picker available (a `group` was passed, **or** `offer_choice` was left at its default `False`) — freezes the session into today's exact pre-feature behavior |
| `all_items` | `list[VocabularyItem]` | **new** — the full loaded pool, unfiltered; `self.items` (existing field) becomes the *active* (chosen-collection) subset, exactly as it already is today when `group_locked` |
| `items` | `list[VocabularyItem]` | unchanged meaning — the pool the current practice pass walks through |

All other existing fields (`current_index`, `pending_attempt`,
`last_correction`, `correct_count`, `warnings`, `progress_file`) are
unchanged in meaning; `select_collection()`/`restart()` reset the ones
that already get reset by existing transitions (see below).

### State machine — new step and transitions

```text
                                  ┌─── group_locked=True (a group was given, OR ────┐
                                  │    offer_choice=False — the default for every   │
                                  │    caller that doesn't pass it): recall ⇄ ...   │
                                  │    exactly as today, "choose" never appears,    │
                                  │    "complete" stays a dead end                  │
                                  └───────────────────────────────────────────────────┘

  group_locked=False (only when offer_choice=True and group=None —
  set by src/web/__main__.py exactly when --group is omitted):

     choose ──select_collection(key)──▶ recall ──...existing flow...──▶ complete
        ▲                                                                   │
        └──────────────────────────── restart() ──────────────────────────┘
```

| Method | Valid from | Goes to | Side effects |
|---|---|---|---|
| `select_collection(key)` (**new**) | `"choose"` | `"recall"` (chosen collection non-empty) or `"empty"` (defensive fallback — not reachable via the real UI) | Filters `self.all_items` by `key` into `self.items`; resets `current_index=0`, `pending_attempt=None`, `last_correction=None`, `correct_count=0` |
| `restart()` (**new**) | `"complete"`, and only when `not group_locked` | `"choose"` (reload found items) or `"empty"` (reload found none) | Re-runs `load_vocabulary(self.vocab_dir)`; replaces `self.warnings`/`self.all_items`; does not touch `self.items`/`current_index` (a fresh `select_collection()` call will) |

Both raise `WrongStepError` outside their valid step (and `restart()` also
raises it when `group_locked` is `True`), matching every existing
transition method's convention (`submit_answer`, `submit_sentence`,
`skip_sentence`, `continue_to_next`).

`continue_to_next()` is **unchanged**: on `"complete"` it remains a no-op
regardless of `group_locked` — `restart()` is the only new way out of
`"complete"`, and only when the interactive (non-locked) path is active.

## `state()` — new/changed shape

| `step` | Fields (beyond existing `warnings`) |
|---|---|
| `"choose"` (**new**) | `collections` (list, per the derived view above) |
| `"complete"` | existing `total`/`correct`, **plus new** `can_restart` (`bool`) — `true` iff `not group_locked` (lets the client show/hide a "practice again" control without needing to know about `group_locked` itself) |
| all other steps | unchanged |

## Progress log — unchanged

Each `PracticeAttempt` (completed or skipped) is still appended to the one
`--progress-file` for the whole process lifetime, regardless of which
collection produced it — no new field, no per-collection log separation.
An attempt's `item` field (the English expression) already lets the log be
read back and understood without needing to know which collection was
active when it was recorded.
