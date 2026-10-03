# Contract: Import Progress and Preview UI

Implemented in:

- `src/web/templates/index.html`;
- `src/web/static/app.js`, in the `--- word-list upload` section;
- `src/web/static/style.css`.

This covers FR-018 to FR-022 and US1 to US4.

**No redesign (FR-022)**: the "Upload word list" buttons, the file input,
its accepted types, the "My word lists" section and its Delete buttons
keep their markup, placement and behaviour. All new UI lives in one new
container, `#import-panel`. It sits inside the existing `#upload-area`,
directly after `#upload-result`, and uses the existing Broadsheet tokens
and classes: `btn`, `btn-secondary`, `btn-ghost`, `label`, `text-muted`
and `option-hint`. Screenshots are verified with the `frontend-design`
skill's recipe at desktop and mobile widths.

## Flow

1. The learner picks a file with the existing button. `app.js` posts it to
   `POST /api/word-lists/import`; the legacy endpoint is no longer used by
   the UI.
   - On `409 {"pending": true}`, the UI asks: `confirm("You have an
     unfinished import of “<source_filename>”. Discard it and start this
     one?")`. On yes, it re-posts with `discard_pending=true`.
   - Errors (`400`, `413`, `415`, `422`) are shown through the existing
     `showUploadResult`, exactly as today.
2. On `202`, `#import-panel` is shown and rendered from the Import State.
   It is polled every 1000 ms with `GET /api/word-lists/import` while the
   status is `running`.
3. On page load, and whenever the choose screen renders, the UI calls
   `GET /api/word-lists/import`. A pending import is shown again, so the
   learner can leave and come back.

## Status line (`#import-status`, `role="status"`, `aria-live="polite"`)

| status | Text |
|---|---|
| running | `Enriching vocabulary: {done} / {total}`, with a `<progress max={total} value={done}>` |
| completed | `Enrichment complete — review {total} words below.` |
| partially_failed | `{enriched_count} enriched, {failed_count} failed — retry the failed words or save the rest.` |
| failed | `{failure_reason}` plus `{done} / {total} enriched so far.` (styled as an error) |
| interrupted | `Enrichment was interrupted at {done} / {total}. Press Retry to continue.` |

These rules keep the display honest:

- The numbers always come from the server's counts, never from an
  estimate (SC-006).
- No percentage is shown.
- While the status is `running`, the file input and both upload buttons
  are disabled. The Retry and Save buttons are also disabled, which
  prevents duplicate requests (FR-020). The server enforces the same rule
  regardless.

## Preview (`#import-preview`, a `<table>` that becomes stacked cards below 600 px)

The columns are **English | IPA | 中文 | Alternates | Status**.

Each row shows the following:

- **English**: shown exactly as uploaded.
- **IPA**: `/ipa/`. When `ipa_review` is set, the cell shows a
  "Pronunciation needs review" badge with the reason as its title text.
  It is never left blank without explanation.
- **中文**: the Chinese meaning. For a failed item, `—`.
- **Alternates**:
  - kept alternates, comma-separated, or `none`;
  - any `dropped_alternates` in muted text, "not used: enthusiastic", so
    the learner can see the filter acted.
- **Status**:
  - `waiting` → "Waiting"; `enriching` → "Enriching…";
  - `enriched` → "Ready";
  - `failed` → "Failed: {error}" with a per-row **Retry** button;
  - `duplicate` → "Repeated — already above".
- **Existing entry** (when `existing` is set):
  - The row shows the badge `Already in your words (“{list}”)`, or
    `Also in the shared words` when the source is `shared`.
  - Below it, the stored values are shown as "Now: /ipa/ · 中文 ·
    alternates".
  - For `source: own`, a two-option control posts to
    `/api/word-lists/import/choice`:
    - **Keep mine**, the default;
    - **Update with this**.

## Actions (`#import-actions`)

| Button | Shown when | Does |
|---|---|---|
| **Retry failed** | `failed_count > 0`, or the status is `failed` or `interrupted` | `POST /retry {}` |
| **Save {savable_count} words** (primary) | The status is not `running` and there is something to save | `POST /confirm`. On `409 exists`: `confirm("Replace your list “{name}”?")`, then `POST /confirm {"replace": true}` |
| **Discard** (ghost) | Always | `confirm("Discard this import? Nothing will be saved.")`, then `DELETE` |

- The Save label adds ` — {left_out} left out` when some words are
  excluded (FR-014).
- After a successful save, the panel is hidden and `fetchState()` runs.
  `showUploadResult` then reports:
  `Added {added} words to “{name}”.`, `Updated {updated} existing words.`
  (only when `updated` > 0), `Left out {left_out}.` (only when
  `left_out` > 0), and the same first-list and locked-session tail lines
  as 016.

## Text changes outside the panel

- `#upload-format-hint`:
  `One word per line — just the English is enough; meanings and
  pronunciations are filled in for you to review. Or add your own:
  receive, 收到, /rɪˈsiːv/ — or a .csv / .md file.`
- The import endpoint's 422 "No words found" hint is: `No words found. Put
  one English word per line — or upload a .md vocabulary file.` The
  legacy `POST /api/word-lists` message is unchanged.
