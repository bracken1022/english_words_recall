# Contract: Pending Import File

**Path**: `word-lists/<username>/.pending-import.json`. There is at most
one such file per account. It is read and written only by
`src/services/enrichment.py::PendingImportStore`. This covers FR-003 and
the restart edge case.

## Format

The file is UTF-8 JSON, written with `ensure_ascii=False` and
`indent=2`, so a person can read it. Fields are as in
[data-model.md](../data-model.md) (`PendingImport`, `ImportItem`). The
derived counts are **not** stored.

```json
{
  "version": 1,
  "list_name": "z-words",
  "source_filename": "z-words.txt",
  "created_at": "2026-10-03T09:15:00+00:00",
  "status": "partially_failed",
  "failure_reason": null,
  "upload_skipped": [],
  "items": [
    {
      "english": "zealous", "position": "line 1",
      "supplied": {"alternates": []},
      "state": "enriched", "ipa": "ˈzeləs", "ipa_review": null,
      "chinese": "热心的；热情的", "alternates": [], "dropped_alternates": ["enthusiastic"],
      "error": null, "existing": null, "choice": "keep", "duplicate_of": null
    }
  ]
}
```

## Rules

- **Atomic writes**: the file is written to a temp file in the same
  folder, then moved into place with `os.replace`. A crash never leaves a
  half-written file.
- **Write timing**: the file is written after each item finishes, and on
  every status or choice change. A restart therefore loses at most the
  item that was being enriched.
- **Restart recovery**: when a file is loaded with `status: running`, every
  `enriching` item becomes `waiting` and the status becomes
  `interrupted`. The file is then rewritten. Nothing restarts
  automatically.
- **Unreadable files**: if the file is not valid JSON, or has a
  `version` other than 1, it is treated as absent and renamed to
  `.pending-import.broken-<timestamp>.json`, so nothing is deleted
  silently. A warning is logged.
- **Invisibility**:
  - The name doesn't end in `.md`, so `load_vocabulary()`, `WordListStore.list()`,
    `_lists()`, `effective_dir()` and `word_source()` all ignore it.
  - An account whose only file is a pending import still practices from
    the shared folder.
- **Deletion**: the file is deleted on a successful confirm or on a
  discard. It is not otherwise removed or expired.
- **Privacy**: the file holds only the uploaded words and the enrichment
  data, and is never sent anywhere. Words go only to the local model
  (Constitution III).
