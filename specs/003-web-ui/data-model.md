# Data Model: Web UI for Remote Access

No new persisted entities. This feature reuses, unchanged, the entities
already defined in `specs/001-vocab-recall-tutor/data-model.md`
(`VocabularyItem`, `PracticeAttempt`, `LearnerProgressLog`) — the web layer
reads/writes them through the exact same `vocabulary_loader` and
`progress_log` services the CLI already uses.

## Runtime-only concept: `PracticeSession`

Not persisted — exists only in server process memory for the lifetime of
one `python -m src.web` run (per research.md "Session/state model").

| Field | Type | Notes |
|---|---|---|
| `items` | `list[VocabularyItem]` | The filtered pool, loaded once at server startup (per the `--group` flag, if any). |
| `current_index` | `int` | Position in `items`; advances by exactly 1 on `/api/continue`, never decreases. |
| `step` | `"empty" \| "recall" \| "sentence" \| "feedback" \| "complete"` | See State Transitions below. |
| `pending_attempt` | `PracticeAttempt \| None` | Built incrementally: `answer`/`correct`/`timestamp`/`item` are set when the recall step completes; `sentence`/`feedback` are added when the sentence step completes. Written to the progress log and cleared when the learner continues. |
| `warnings` | `list[str]` | Vocabulary-loading warnings captured at startup (malformed blocks), surfaced to every page load per FR-017. |

### State Transitions

```text
        (no items loaded)
              │
              ▼
           "empty" ──────────────────────────────────► (stays empty; no further transitions)

        (items loaded, current_index = 0)
              │
              ▼
           "recall"  ──POST /api/answer──►  "sentence"  ──POST /api/sentence──►  "feedback"
              ▲                                                                      │
              │                                                                      │
              └──────────────────────── POST /api/continue ─────────────────────────┘
                        (advances current_index by 1; if current_index == len(items),
                         step becomes "complete" instead of "recall")
```

- **Validation rule**: a request for the wrong step (e.g., `POST
  /api/sentence` while `step == "recall"`) is rejected (see
  `contracts/web-api-contract.md`) rather than silently accepted — this is
  what keeps `current_index`/`pending_attempt` consistent without needing a
  database or transaction of any kind.
- **Validation rule**: `POST /api/continue` is only valid from `step ==
  "feedback"` (or `"complete"`, where it's a no-op) — it is not valid to
  jump from `"recall"` or `"sentence"` straight to the next item, matching
  the existing "no skip" rule (`001`'s FR-016) carried over to the web UI.

## Relationships

```text
PracticeSession.items[current_index]  --is-the-target-of-->  pending_attempt
pending_attempt  --written-to-->  LearnerProgressLog (via services/progress_log.py, unchanged)
```

`PracticeSession` has no relationship to any new stored entity — it is
exactly the same information `session.py`'s `run_session` loop already
holds in local variables for the CLI, now held across HTTP requests instead
of within one function call.
