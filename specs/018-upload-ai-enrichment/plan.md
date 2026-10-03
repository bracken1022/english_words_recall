# Implementation Plan: Local-AI Enrichment of Uploaded Word Lists

**Branch**: `018-upload-ai-enrichment` | **Date**: 2026-10-03 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/018-upload-ai-enrichment/spec.md`

## Summary

When a learner uploads a word list in the web UI, it no longer saves
straight away. Instead the upload creates a **pending import**: the words
are extracted, and a background worker enriches them one word at a time:

- the local Ollama model supplies a concise Chinese meaning and
  spelling-variant alternates;
- the American IPA comes from the offline CMU Pronouncing Dictionary,
  converted to the OALD NAmE style. (The first design asked the model
  for IPA as well; that was revised after the evaluation in
  eval-report.md. See research R4.)

Every model reply is untrusted. Deterministic validators decide what is
kept:

- an American-IPA checker, applied to the dictionary values too;
- a heteronym and acronym list that marks pronunciations for review;
- Chinese length and shape rules;
- a spelling-variant-only alternates filter.

The UI polls and shows "Enriching vocabulary: n / total", then a preview
in which:

- existing entries are flagged (keep or update);
- failed words can be retried;
- the model being unavailable keeps the whole upload.

On confirm, the words are written all-or-nothing in the existing
vocabulary Markdown format to `word-lists/<user>/<list>.md`, so "My Word
Lists" and practice pick them up unchanged.

Spec 016's `POST /api/word-lists` stays byte-for-byte compatible. The UI
moves to new `/api/word-lists/import` routes.

## Technical Context

**Language/Version**: Python 3.11+; vanilla JS, HTML and CSS

**Primary Dependencies**: the existing Flask, requests and PyYAML; Ollama
`/api/chat` at `--ollama-url` with `--model`. One new dependency,
`cmudict`, provides the CMU dictionary data file (the data is BSD; the
package wrapper is GPL-3.0 and is not called). It was added on
2026-10-03 with the product owner's approval (research R4).

**Storage**:

- Vocabulary Markdown files, unchanged in format.
- New: one JSON workflow file per account,
  `word-lists/<user>/.pending-import.json` (research R1). It is
  invisible to the vocabulary loaders.

**Testing**:

- `pytest` with a mocked `requests.post`, using the pattern already in
  `tests/contract/test_ollama_correction_contract.py`.
- The Flask test client.
- An opt-in live evaluation tool, `src/tools/eval_enrichment.py`, for
  model quality.

**Target Platform**: local machine running the tutor and Ollama; browsers
on the household LAN, desktop and phone

**Project Type**: single project: Python web app plus CLI (`src/`)

**Performance Goals**:

- Progress advances visibly after each word, at roughly 3–8 s per word
  on the local `qwen3:14b`.
- A 40-word list finishes in a few minutes.
- The UI poll costs one cheap GET per second.

**Constraints**:

- Fully local; no cloud calls (FR-004).
- The model decides no paths, names or workflow (FR-006).
- Invalid output is never written (FR-012).
- Existing files stay byte-identical unless the learner opts to update
  them (SC-007).
- No regressions in the 016 and 017 contracts (SC-008).

**Scale/Scope**:

- A few household accounts, each with at most one pending import.
- At most 5,000 words per upload, which is the existing limit.
- Typical lists have 20–100 words.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | How this plan satisfies it | Status |
|---|---|---|
| **I. Test-First** | `tasks.md` will order contract and unit tests before each implementation step. The tests cover: the validators (pure functions), the enrichment client with a mocked Ollama, the pending store (restart recovery), the worker (per-item failure, unavailable model, cancel, duplicate start), the import API (every row of the contract tables), all-or-nothing confirm with injected I/O failure, and isolation. The existing tests stay untouched as the regression net. | ✅ |
| **II. Pedagogical Accuracy & Safety** | Generated content is reviewed by the learner before it is saved. Uncertain pronunciations are flagged rather than guessed (heteronym list, acronym rule, model flag, IPA checker). Broad synonyms are made impossible by a deterministic filter. There is a reviewed evaluation fixture plus `eval_enrichment`, which must meet SC-002/SC-003 before release. Content safety: the output is constrained to IPA symbols, ≤ 40-character Chinese glosses and spelling variants of the learner's own word, which leaves no room for free-form harmful text. | ✅ |
| **III. Learner Data Privacy** | Only the uploaded words and the enrichment data are stored, in the learner's own folder, and deleted on confirm or discard. Words go only to the local model, and only the word itself plus any learner-supplied meaning. This is documented in spec "Data Handling" and contracts/pending-import-file.md. | ✅ |

No violations, so Complexity Tracking is empty.

**Post-design re-check (after Phase 1)**: ✅. The contracts keep the model
out of every control decision: the worker's state machine is driven only
by outcome classes and the validators. The legacy endpoint is unchanged.
The pending file is account-scoped and not exported anywhere.

## Project Structure

### Documentation (this feature)

```text
specs/018-upload-ai-enrichment/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── import-api-contract.md
│   ├── enrichment-llm-contract.md
│   ├── enrichment-validation.md
│   ├── pending-import-file.md
│   └── import-ui-contract.md
├── checklists/requirements.md
└── tasks.md              # /speckit-tasks
```

### Source Code (repository root)

```text
src/
├── lib/
│   ├── ipa.py                  # + check_american_ipa, is_heteronym, shared stress helper
│   ├── us_pronunciation.py     # NEW: CMUdict lookup + ARPABET → OALD NAmE IPA
│   └── alternates.py           # NEW: canonical(), is_spelling_variant(), filter_alternates()
├── services/
│   ├── llm_client.py           # _post_json refactor: distinguish unavailable vs bad reply (behaviour unchanged)
│   ├── enrichment_client.py    # NEW: request_enrichment() → EnrichmentReply
│   ├── enrichment.py           # NEW: PendingImport/ImportItem, PendingImportStore, validate_item,
│   │                           #      build_import (dup + existing detection), EnrichmentRunner (thread)
│   └── word_lists.py           # + DraftWord, parse_upload(require_chinese=...), WordListStore.apply_import
├── tools/
│   └── eval_enrichment.py      # NEW: opt-in live model evaluation
└── web/
    ├── app.py                  # + /api/word-lists/import routes; runner wired to OLLAMA_URL/MODEL
    ├── templates/index.html    # + #import-panel inside #upload-area; hint text
    └── static/
        ├── app.js              # upload → import flow, polling, preview, actions
        └── style.css           # panel/preview/badge styles with existing tokens

tests/
├── fixtures/
│   ├── enrichment_eval.yml     # NEW: reviewed eval set (≥50 words, ≥20 traps, ≥10 variants)
│   └── american_ipa.yml        # NEW: reviewed OALD NAmE transcriptions
├── contract/
│   ├── test_import_api_contract.py         # NEW
│   ├── test_enrichment_llm_contract.py     # NEW
│   └── test_pending_import_file_contract.py# NEW
├── integration/
│   └── test_import_flow.py                 # NEW: upload→enrich→preview→confirm, failures, restart, isolation
└── unit/
    ├── test_alternates.py                  # NEW
    ├── test_american_ipa.py                # NEW
    ├── test_us_pronunciation.py            # NEW
    ├── test_enrichment_validation.py       # NEW
    ├── test_enrichment_runner.py           # NEW
    └── test_word_list_parsing.py           # + require_chinese=False cases (existing cases untouched)
```

**Structure Decision**: this is the existing single-project layout. The
new logic sits in `src/services/enrichment*.py` and `src/lib/alternates.py`
so that `llm_client.py` (sentence review) and the 016 upload path stay
behaviourally untouched.

## Key Design Decisions

The rationale for each is in [research.md](research.md).

1. **The pending import is a hidden JSON file** in the account's
   word-list folder. It survives restarts and is ignored by the loaders
   (R1).
2. **A background thread per import**, processing words sequentially, with
   the UI polling once a second. The per-account lock and status check
   prevent duplicate batches (R2).
3. **The model client separates two failure kinds.** An `unavailable`
   model stops the batch and keeps the waiting items. A `bad_reply` fails
   only that item (R3).
4. **American IPA from an offline dictionary, OALD NAmE style**, and still
   enforced by a checker. A word that is missing, ambiguous, a heteronym
   or an abbreviation becomes "needs review" with no IPA. That never
   blocks the word, and nothing unchecked is written (R4).
5. **Alternates come from the model only if they are deterministic
   spelling variants.** The learner's own alternates are kept (R6).
6. **Existing entries**: own-list matches default to *keep*, and *update*
   rewrites only those blocks. Shared-folder matches are included in the
   new list, and the shared folder is never written (R7).
7. **All-or-nothing confirm** across the new list and any updated lists,
   using temp files, backups and rollback (R8).
8. **The legacy 016 endpoint is unchanged.** The UI switches to the new
   import routes (R9).
9. **Two-layer accuracy check**: mocked unit tests for the guards, plus a
   live evaluation against a reviewed fixture before release (R10).

## Risks

- **Model speed on large lists.** A 1,000-word upload could take an hour
  or more. This is mitigated by:
  - resumable progress;
  - the learner being able to leave the page;
  - Save being available for the enriched part once the batch stops
    (`completed`, `failed` or `interrupted`), with the left-out words
    kept for retry.

  A "pause" action is a possible follow-up; it is not in this spec.
- **The model writes wrong IPA.** This happened: in the first
  evaluation, 21 of 50 words were wrong. It was resolved by taking IPA
  from the CMU dictionary instead (R4).
- **Words missing from the dictionary** (rare words, new coinages) get
  "needs review" and no IPA. This is acceptable, since learners can
  supply `/ipa/` themselves.
- **Mixed accents in a learner's collection.** The spec accepts this
  (clarified 2026-10-03). The display is unchanged.

## Complexity Tracking

No constitution violations.
