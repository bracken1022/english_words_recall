# Implementation Plan: Part of Speech for Vocabulary

**Branch**: `main` (commits go straight to main) | **Date**: 2026-10-05 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/019-part-of-speech/spec.md`

## Summary

Each vocabulary entry gains an optional `pos` field. It is an ordered
list of labels from a fixed set (`n.`, `v.`, `adj.`, …, `phr. v.`,
`phr.`). It is shown as short italic labels **before the Chinese
meaning**, during recall, on the reveal, and on the sentence and
feedback steps, in the web UI and the CLI.

- **New uploads**: spec 018's enrichment asks the local model for `pos`
  in the same request as the meaning. The labels are validated against
  the fixed set, and anything outside it gets "part of speech needs
  review". Generated meanings have part-of-speech notes like
  "（动词）" stripped.
- **Existing words**: all about 710 (shared folder and every uploaded
  list) are filled once with a new `add_pos` tool. It is built like
  spec 017's `add_ipa`: a reviewed mapping, backups, insert-only edits,
  a verify-or-restore step, and a REVIEW.md with a spot check.

## Technical Context

**Language/Version**: Python 3.11+; vanilla JS, HTML and CSS

**Primary Dependencies**: existing only (Flask, PyYAML, requests, rich;
Ollama). No new dependencies.

**Storage**: vocabulary Markdown files gain an optional `pos:` line. The
spec 018 pending-import JSON gains two fields per item, both with
defaults. Learner data (`vocabulary/`, `word-lists/`) is edited in place
by the one-off fill, with backups in the gitignored `backups/`.

**Testing**: pytest (unit, contract and integration); static-asset
string tests for JS, HTML and CSS; `eval_enrichment` on the real model;
screenshot verification with the `frontend-design` recipe.

**Target Platform**: local tutor server and browsers on the household LAN
(desktop and phone); the CLI in a terminal

**Project Type**: single project (`src/`, `tests/`)

**Performance Goals**: no extra request per word; the label comes in the
existing enrichment reply (SC-005).

**Constraints**:

- Fully local (FR-006).
- Grading is untouched (FR-010).
- Files without `pos` load with 0 new warnings (FR-003, SC-004).
- Existing tests are unchanged.

**Scale/Scope**: about 710 existing words to fill; 12 labels.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | How this plan satisfies it | Status |
|---|---|---|
| **I. Test-First** | Every step in tasks.md starts with failing tests: normaliser, loader, parser, state, rendering strings, enrichment rules, fill tool. Existing tests act as the regression net. | ✅ |
| **II. Pedagogical Accuracy & Safety** | Labels come from a closed set, and anything else is flagged, never saved. Generated labels are measured on the real model against a reviewed reference set (≥ 95%, SC-002). The existing-word fill uses a reviewed mapping, classified from each word's own meanings, and words that can't be classified are left empty with a reason. A 30-word human spot check is done (SC-006). | ✅ |
| **III. Learner Data Privacy** | No new data is collected. The fill edits learners' own files locally, with backups. Nothing leaves the machine. | ✅ |

No violations.

**Post-design re-check**: ✅. The contracts keep grading free of `pos`.
The model's labels pass through `normalize_pos` before they are stored.

## Project Structure

### Documentation (this feature)

```text
specs/019-part-of-speech/
├── plan.md, research.md, data-model.md, quickstart.md
├── contracts/
│   ├── pos-field-format.md
│   ├── pos-display-contract.md
│   ├── enrichment-pos-delta.md
│   └── add-pos-tool-contract.md
├── checklists/requirements.md
└── tasks.md            # /speckit-tasks
```

### Source Code (repository root)

```text
src/
├── lib/pos.py                     # NEW: labels, names, normalize_pos, is_pos_field, strip_pos_notes
├── models/vocabulary_item.py      # + pos, pos_problem
├── services/vocabulary_loader.py  # + pos warning
├── services/word_lists.py         # + pos in DraftWord, simple-list pos field, _to_markdown key order, update map
├── services/enrichment_client.py  # + pos in schema/prompt/reply
├── services/enrichment.py         # + ImportItem.pos/pos_review, validate_item rules, meaning note stripping
├── web/session_state.py           # + state()["pos"]
├── web/static/app.js, style.css   # + span.pos-list rendering
├── web/templates/index.html       # hint text
├── cli/session.py                 # + labels in recall prompt
└── tools/
    ├── add_pos.py                 # NEW: one-off fill (shares helpers with add_ipa)
    └── eval_enrichment.py         # + part-of-speech accuracy

tests/
├── unit/test_pos.py, test_add_pos_tool.py          # NEW
├── fixtures/enrichment_eval.yml                    # + pos / pos_ok, multi-class words
└── (additions to existing test files only)
```

**Structure Decision**: the existing single-project layout. Part-of-speech
logic lives in one small library module, `src/lib/pos.py`, used by the
loader, the parsers, enrichment and the fill tool.

## Key Decisions

The rationale for each is in [research.md](research.md).

1. `pos` is a YAML list of display labels. Many spellings are accepted
   on input, and it is always written in one form (R1, R2).
2. In simple lists, only dotted, full-name or Chinese labels count, so
   alternates are never misread (R2).
3. Labels are shown during recall, as a dictionary-style hint before the
   meaning (R3, spec Q1).
4. Upload labels come from the same model reply as the meaning, are
   validated against the closed set, and are flagged rather than saved
   when invalid (R4).
5. Existing words are filled once from a reviewed mapping by `add_pos`,
   which mirrors `add_ipa` (R5, spec Q2).
6. Real-model accuracy is gated in `eval_enrichment` before release (R6).

## Risks

- **The model's labels miss the 95% gate.** The fallback is decided with
  the user, as in spec 018. Options include a lexical database or
  manual labels.
- **About 710 words to classify by hand.** Words are classified from
  their own Chinese meanings, so the labels are consistent with what the
  learner sees. Unclear words are left empty, and the spot check
  measures accuracy.
- **Old meanings with embedded "（动词）"** stay as written (out of scope),
  so a word may show `n. v.` and a note in its meaning.

## Complexity Tracking

No constitution violations.
