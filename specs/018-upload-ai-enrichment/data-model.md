# Data Model: Local-AI Enrichment of Uploaded Word Lists

This feature does not change the stored vocabulary entities
(`VocabularyItem` and the Word List `.md` files from specs 001, 016 and
017). It adds the transient entities below.

## DraftWord (`src/services/word_lists.py`)

An extracted upload entry that may be incomplete. It is produced by
`parse_upload(..., require_chinese=False)`.

| Field | Type | Notes |
|---|---|---|
| `english` | str | Trimmed and otherwise exactly as uploaded. Must not be empty: a line or block without it is still skipped, as in 016. |
| `chinese` | str \| None | As supplied, or None. |
| `ipa` | str \| None | As supplied and normalised by `normalize_ipa`, or None. |
| `alternates` | list[str] | As supplied, possibly empty. |
| `position` | str | `"line 12"` or `"block 3"`, used in messages. |

`parse_upload(..., require_chinese=True)`, the default and legacy path,
still returns `VocabularyItem`s and skips entries without Chinese, exactly
as before.

## PendingImport (`src/services/enrichment.py`)

There is at most one per account. It is persisted at
`word-lists/<username>/.pending-import.json`; see
[contracts/pending-import-file.md](contracts/pending-import-file.md).

| Field | Type | Notes |
|---|---|---|
| `version` | int | `1` |
| `list_name` | str | Taken from `sanitize_list_name(file stem)`, as in 016; empty means the "My words" fallback. **Never** set by the model. |
| `source_filename` | str | Used for display only. |
| `created_at` | ISO-8601 str | |
| `status` | enum | `running`, `completed`, `partially_failed`, `failed` or `interrupted`. |
| `failure_reason` | str \| None | Set when the status is `failed`, e.g. `"local AI unavailable"`. |
| `upload_skipped` | list[str] | Skip messages from the parser, in the same format as 016. |
| `items` | list[ImportItem] | In file order. |

Derived values (not stored):

| Name | Definition |
|---|---|
| `total` | Count of items whose `state != "duplicate"`. |
| `done` | Count of items whose `state` is `enriched` or `failed`. |
| `enriched_count` | Count of items whose `state` is `enriched`. |
| `failed_count` | Count of items whose `state` is `failed`. |
| `savable` | Items that are `enriched`, valid, and not an own-list existing entry left on `keep`. |

### Status transitions

```text
                start (upload)
                     │
                     ▼
   ┌──────────── running ─────────────┐
   │   (worker processes waiting      │ server restart
   │    items one by one)             ▼
   │                             interrupted
   │ all items done,                  │ retry
   │ none failed ─► completed         │
   │ some failed ─► partially_failed ◄┘ (→ running)
   │ model unavailable ─► failed (failure_reason)
   │
   └─ retry (from failed / partially_failed / interrupted /
      a single item) ─► running
```

- `confirm` is allowed only when the status is not `running`, and
  `savable` is not empty.
- `discard` is allowed in any state. If the import is running, it sets
  the cancel flag first. Either way the file is deleted.
- A successful confirm deletes the file. A failed confirm leaves it
  untouched.

## ImportItem

| Field | Type | Notes |
|---|---|---|
| `english` | str | Copied from the DraftWord. Never changes. |
| `position` | str | From the DraftWord. |
| `supplied` | `{chinese?, ipa?, alternates?}` | Values from the upload. These are always kept (FR-007). |
| `state` | enum | `waiting`, `enriching`, `enriched`, `failed` or `duplicate`. |
| `ipa` | str \| None | The final bare transcription: either supplied, or looked up in the offline American dictionary and checked. |
| `ipa_review` | str \| None | Set means "pronunciation needs review" and gives the reason, e.g. `"pronunciation depends on the meaning"` or `"not in the pronunciation dictionary"` (contracts/enrichment-validation.md). When set, `ipa` is None. |
| `chinese` | str \| None | The final value, supplied or generated and validated. |
| `alternates` | list[str] | The final list: supplied values plus model values that passed the filter. |
| `dropped_alternates` | list[str] | Model alternates removed by the filter. Shown faintly in the preview for transparency, and never saved. |
| `error` | str \| None | The reason when `state = failed`. |
| `existing` | `{source: "own" \| "shared", list: str, chinese, ipa, alternates}` \| None | Set when the word matches an existing entry (R7). |
| `choice` | `"keep"` \| `"update"` | Only meaningful when `existing.source == "own"`. Defaults to `keep`. |
| `duplicate_of` | int \| None | The index of the first occurrence when `state = duplicate`. |

### Item state transitions

```text
waiting ─► enriching ─► enriched
                     └► failed ─(retry)─► waiting
(interrupted restart: enriching ─► waiting)
duplicate is terminal and never sent to the model
```

An item whose supplied fields already include Chinese **and** valid IPA,
or a supplied IPA kept as given, goes straight from `waiting` to
`enriched` without a model call.

### Validation (an item may become `enriched` only if all hold, FR-012)

The full rules are in
[contracts/enrichment-validation.md](contracts/enrichment-validation.md).

- `english` is not empty and equals the DraftWord's `english`.
- Exactly one of `ipa` and `ipa_review` is set.
- `chinese` passes the Chinese rules (R5).
- `alternates` is a list of distinct, non-empty strings, none equal to
  `english` (case-insensitive), with at most 5 entries, each no longer
  than 64 characters.

## EnrichmentReply (`src/services/enrichment_client.py`)

This is the model's parsed reply. It is untrusted.

| Field | Type |
|---|---|
| `outcome` | `ok`, `unavailable` or `bad_reply` |
| `chinese` | str \| None |
| `alternates` | list[str] |
| `detail` | str \| None (the reason for `bad_reply`) |

Only these fields are ever read from the model's output.

## Effect on saved files at confirm

Rendered with the existing `_to_markdown` field order: `english`, `ipa`
(when present), `alternates`, `chinese`, `group`.

- **New list** `word-lists/<user>/<list_name>.md`: one block per savable
  item that is not an own-list existing entry. `group` is the list name.
  A word marked "needs review" is saved without an `ipa` key.
- **Updated own lists**: only the matched blocks' `ipa`, `chinese` and
  `alternates` change. The edit works on the file's raw parsed YAML
  dicts, so other blocks keep every key and value exactly, including an
  invalid `ipa` they may carry. The file is then re-dumped in the same
  style. A file with no updated block is not touched at all.
