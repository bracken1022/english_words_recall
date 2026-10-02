# Contract: Showing the Pronunciation (web state, web UI, CLI)

Covers spec FR-003, FR-004, SC-003, SC-004.

## Web state — `GET /api/state` (and every endpoint that returns state)

| `step` | `ipa` |
|---|---|
| `choose`, `empty`, `complete`, `recall` | **key absent** |
| `reveal`, `sentence`, `feedback` | `"rɪˈsiːv"` (bare) or `null` |

The `ipa` value comes from the current item. It appears in exactly the
same branch of `state()` that adds `accepted_expressions`.

## Web UI (`src/web/static/app.js`, `index.html`, `style.css`)

Rendered as `<span class="ipa" lang="en-GB-fonipa">/rɪˈsiːv/</span>`,
built with `textContent`. Nothing at all is rendered when `ipa` is `null`.

| Place | Where the `.ipa` goes |
|---|---|
| Recall result, correct (`renderRecallResult`) | right after the stamp in `#word-feedback` |
| Recall result, wrong or "Show answer" | inside `.answer-reveal`, right after `.answer-text` |
| Sentence step (`renderSentence`) | `#target-ipa` beside `#target-expression` in `.target-row` (cleared when `null`) |
| Feedback (`renderFeedback`) | inside `.feedback-head`, after the `h2` word |

Styling:
- `.ipa` uses the body serif at a size a little smaller than the word,
  `color: var(--color-muted)`, `font-style: normal`, and
  `white-space: nowrap`;
- it wraps under the word at ≤ 600px;
- no new colours.

## CLI (`src/cli/session.py`)

- **Recall** (`run_recall_step`): after the existing `Correct!` or
  `Incorrect.` line, an item with IPA prints a second line,
  `Pronunciation: /rɪˈsiːv/`. Nothing is printed when `ipa` is `None`.
  Nothing is printed before the answer is submitted.
- **Sentence step** (`run_sentence_step(target_expression, ..., ipa=None)`):
  the prompt becomes `Write a sentence using "receive" /rɪˈsiːv/:` when
  `ipa` is given, and is unchanged otherwise. `run_session` passes
  `item.ipa`.
