# Contract: Removing a Word During Practice (web API)

These routes exist only in accounts mode with a word-list store (spec
016). Otherwise they return `404`. The login guard from spec 015
applies.

## `POST /api/remove-word`

This removes the current word: from the learner's own list file when it
came from there, or by hiding it for this learner when it came from the
shared folder.

| Case | Status | Body |
|---|---|---|
| Step is `recall`, `reveal` or `sentence` | `200` | `{"state": <state>, "removed": {"english": "…", "chinese": "…"}, "undo": true}` |
| Any other step | `409` | `{"error": "There's no word to remove right now."}` |
| The word is no longer in its file (e.g. removed on another device) | `200` | Removed from the session anyway, with `"undo": false` |
| The file couldn't be written | `500` | `{"error": "Couldn't remove the word; nothing was changed."}`, and the session is unchanged |

- **Own lists**: the file loses exactly that entry; every other byte is
  unchanged.
- **Attempts**: an attempt held at `reveal` or `sentence` is logged as
  it would be on continue or skip.

## `POST /api/undo-remove`

| Case | Status | Body |
|---|---|---|
| A removal is pending undo | `200` | `<state>`: the word is back as the current word, at `recall` |
| Nothing to undo (none yet, or another action came first) | `409` | `{"error": "Nothing to undo."}` |
| The file couldn't be written | `500` | `{"error": "Couldn't restore the word."}`; the removal stays pending, so Undo can be tried again |

- **Own lists**: the file is byte-identical to before the removal, unless
  it was changed in between; see research R2.
- **Shared words**: the hidden entry is deleted.

## Isolation

- A learner's removals only ever touch `word-lists/<username>/`.
- The shared vocabulary folder is never written.
