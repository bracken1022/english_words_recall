# Contract: `.corrections.json`

One per word folder: `vocabulary/.corrections.json` (shared sets, applies
to everyone) and `word-lists/<account>/.corrections.json` (that
learner's own lists). UTF-8 JSON, written atomically (temp file in the
same folder, then `os.replace`), under a per-file lock.

```json
{
  "version": 1,
  "overlay": {
    "T_words.md|t-words|tailor|裁缝；定制；使适合": {
      "ipa": "ˈteɪlə",
      "chinese": "裁缝；定做（衣服）；使适应",
      "pos": ["n.", "v."]
    }
  },
  "checked": ["3f2a…", "9be0…"],
  "records": [
    {
      "id": "a1b2c3d4e5f6",
      "batch": "0f9e8d7c6b5a",
      "file": "T_words.md",
      "group": "t-words",
      "english": "tailor",
      "origin_chinese": "裁缝；定制；使适合",
      "field": "chinese",
      "old": "裁缝；定制；使适合",
      "new": "裁缝；定做（衣服）；使适应",
      "at": "2026-10-21T09:30:00Z",
      "undone_at": null
    }
  ]
}
```

## Rules

- `overlay` is only written in the shared folder. The loader applies an
  entry to the word whose file, group, English and **file meaning**
  match the key; fields in the entry replace the file's values. Unknown
  keys (the word was removed or edited in the file) are ignored.
- An overlay entry holds all three fields (the word's full corrected
  values), so applying it never mixes two checks.
- `checked`: fingerprints (data-model.md), at most 20,000; oldest
  dropped first.
- `records`: newest first, at most 500.
- Readers tolerate a missing file, invalid JSON, a wrong `version` or
  wrong types by treating that part as empty, and never fail loading or
  practice. Writers rewrite the whole file.
- The shared vocabulary `.md` files are never written (SC-006).
- Nothing in this file identifies a learner: no account names, progress
  or attempts.
