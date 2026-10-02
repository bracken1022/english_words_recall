# Data Model: Personal Word Lists per Account

## Account Word Folder (new, on disk)

`<word-lists-dir>/<username>/` — default `word-lists/<username>/`. Created on
first upload. Contains only list files (`*.md`) written by this feature.

**Effective vocabulary folder** (research R2):

```text
effective_vocab_dir(account) =
    word-lists/<username>/   if it contains ≥ 1 "*.md" file
    shared --vocab-dir       otherwise
word_source = "own" | "shared" accordingly
```

## Word List (new — one file per list)

`word-lists/<username>/<name>.md`, in the existing vocabulary Markdown
format (`specs/001-vocab-recall-tutor/contracts/vocabulary-markdown-format.md`).

| Attribute | Source | Rules |
|---|---|---|
| `name` | sanitised upload filename stem | Unicode letters/digits, space, `-`, `_`; whitespace collapsed; no leading `.`/space; 1–64 chars; empty → `My words` (`My words 2`, … if taken). Unique per account **case-insensitively**. |
| `owner` | the logged-in account | Implicit in the folder. |
| `uploaded_at` | file modification time | ISO-8601 in API responses. |
| `word_count` | number of valid blocks in the file | 1–5,000. |
| words | normalised from the upload | Each block: `english`, `chinese`, `alternates` (list, may be empty), `group: <name>` (always the list name — research R4). |

Written atomically (temp file + `os.replace`). Never read from or written to
outside the owner's folder.

### Word List lifecycle

```text
 (none) ──upload name N──▶ exists(N)
 exists(N) ──upload N, replace=false──▶ 409, unchanged
 exists(N) ──upload N, replace=true───▶ exists(N) with new words
 exists(N) ──delete N──▶ (none)
```

Deleting the last list flips the account's `word_source` back to `"shared"`.

## Word (existing — `VocabularyItem`, unchanged)

`english`, `chinese`, `alternates`, `group`. Uploaded words are ordinary
`VocabularyItem`s once saved; grading/review/logging are unchanged.

## Upload Result (API response, not stored)

| Field | Type | Meaning |
|---|---|---|
| `name` | str | Final list (= word set) name. |
| `replaced` | bool | True if an existing list was replaced. |
| `added` | int | Valid words saved. |
| `skipped_count` | int | Entries skipped. |
| `skipped` | list[str] | Up to 20 messages: `"line 12: no Chinese meaning"`, `"block 3: missing 'english'"`. |
| `first_list` | bool | True when this upload switched the account from shared to own words (US2 scenario 6). |
| `applies_now` | bool | False when the server was started group-locked (edge case) — new lists won't show in that mode. |

## Parsed Upload (internal)

`parse_upload(filename: str, data: bytes) -> ParsedUpload(items:
list[VocabularyItem], skipped: list[str])`, raising `UploadFormatError`
(unsupported extension / undecodable text) — `src/services/word_lists.py`.
Validation order and rules: `contracts/upload-formats.md`.

## Changes to existing runtime objects

- **`PracticeSession`** (`src/web/session_state.py`): + `set_vocab_dir(path)`
  — stores the path; reloads vocabulary only when not group-locked and
  `step in ("choose", "empty")`. Nothing else changes.
- **`SessionRegistry`** (`src/web/session_registry.py`): takes a
  `word_lists: WordListStore`; `get()` builds sessions with
  `store.effective_dir(account, shared_vocab_dir)`; + `refresh_vocab(account)`
  calls `set_vocab_dir(...)` on that account's live session (if any).
- **`WordListStore`** (new, `src/services/word_lists.py`): root dir +
  per-account locks; `list(account)`, `save(account, name, items, replace)`,
  `delete(account, name)`, `effective_dir(account, shared)`,
  `folder(account)`.

## Relationships

```text
Account 1 ── 1 Account Word Folder ── 0..N Word List ── 1..5000 Word
Account ──effective_vocab_dir──▶ (own folder | shared vocabulary folder)
PracticeSession (per account) ── reads ──▶ effective vocab folder
Progress history (per account, spec 015) ── unchanged, independent of lists
```
