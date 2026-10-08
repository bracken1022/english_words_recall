# Quickstart: Validating Word Removal

The behaviour is defined in [contracts/](contracts/) and
[data-model.md](data-model.md).

## 1. Automated tests

```bash
.venv/bin/python -m pytest
.venv/bin/ruff check src tests
```

Everything passes, with the pre-existing tests unchanged. The new tests
cover:

- the `source` stamp on loaded words;
- an exact cut and an exact restore in a list file, plus a restore after
  the file has changed;
- hidden shared words, and loading with them filtered out;
- `remove_current` and `undo_remove` at each step;
- the undo window closing on the next action;
- the API status codes;
- account isolation;
- the UI strings.

## 2. Manual check (web UI)

| # | Do | Expect | Result (2026-10-08) |
|---|---|---|---|
| a | Practice one of your own lists, and on a word press **Remove this word**, then OK | The next word appears. The toast says Removed “…” with Undo. The list's count in My word lists drops by 1. | ✅ |
| b | Press **Undo** | The word is back as the current word. `shasum` of the list file matches its value before the removal. | ✅ sha256 identical |
| c | Remove a word, then answer the next one | The toast is gone, and the removal is final. A new session never shows the word. | ✅ undo gives 409 |
| d | Remove a word on the sentence step | The attempt is in the progress history, and the session moves on. | ✅ attempt in history |
| e | As an account with no own lists, practicing the shared sets, remove a word | The shared files are unchanged (`git status vocabulary` is clean). The word never comes back for this account; another account still sees it. | ✅ shared file unchanged; hidden for that account only |
| f | Remove the last word of a session | The completion screen appears. | ✅ |
| g | Phone width (390 px) | The button and the toast are usable. | ✅ button and toast usable at 390 px (`toast-390.png`) |

Scenarios a–f were scripted against the real app in a temporary folder, never the real learner data. Scenario g was checked in screenshots in `design/verification/remove/pass-0/`.
