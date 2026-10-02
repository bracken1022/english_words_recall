# Contract: Word-List Upload & Management UI

Implemented in `src/web/templates/index.html`, `src/web/static/app.js`,
`src/web/static/style.css`, inside the existing `#choose-view` (word-set
screen) and `#empty-view`. Broadsheet style: reuse existing `.label`,
`.btn`, `.btn-secondary`, `.btn-ghost`, `.text-muted`, `.option-hint`; no new
colours or fonts. Covers spec US1–US3.

## Word-set screen additions (`#choose-view`)

- `#word-source-note` (`.option-hint`): "Practicing your own word lists."
  when `state.word_source === "own"`, or "Practicing the shared word sets —
  upload a list to practice your own words." when `"shared"`.
- `#upload-button` ("Upload word list", `.btn-secondary`) opens a hidden
  `<input id="upload-input" type="file" accept=".csv,.txt,.tsv,.md,.markdown">`.
- `#upload-format-hint` (`.option-hint`): "One word per line: `receive,
  收到` — or a .csv / .md file."
- `#upload-result` (`role="status"`): after an upload shows "Added 40 words
  to “unit1”." plus, when `skipped_count > 0`, "Skipped 2:" and the
  `skipped` messages as a list; when `first_list`, "From now on you'll
  practice your own lists."; when `applies_now` is false, "New lists show
  up when the tutor isn't locked to one word set." Errors show the
  response's `error` text instead.
- `#my-lists` section (label "My word lists"), shown only when the account
  has lists: one row per list — name, "42 words · uploaded 2 Oct", and a
  `.btn-ghost` "Delete" button (`data-list-name`).

## Empty screen (`#empty-view`)

When logged in (accounts mode), also shows the same `#upload-button`-style
action (`#empty-upload-button`) so a learner with no words at all can add
some.

## Flows

1. **Upload**: on file chosen → `POST /api/word-lists` (FormData `file`).
   - `409` → `confirm("Replace your list “<name>”?")`; on OK re-post with
     `replace=true`; on Cancel show nothing changed.
   - `200` → show the result, then `GET /api/state` + `GET /api/word-lists`
     and re-render (the new set appears immediately).
   - `401` → login screen (existing `isUnauthorized`).
   - other errors → show `error` in `#upload-result`.
   - The file input is reset after every attempt so the same file can be
     chosen again.
2. **Delete**: `confirm("Delete your list “<name>”? Your practice history
   is kept.")` → `DELETE /api/word-lists/<encodeURIComponent(name)>` → re-render
   state and lists.
3. `GET /api/word-lists` is fetched whenever the choose or empty screen is
   rendered in accounts mode (`state.account` present).

## Accessibility & layout

- Upload button and Delete buttons are real `<button>`s with visible text;
  the result region is announced (`role="status"`).
- At 375–390 px the upload controls and list rows wrap without horizontal
  scroll; touch targets ≥ 44 px (existing mobile rule).
- Legacy mode (no accounts): none of these elements are shown.
