# Implementation Plan: IPA Pronunciation for Vocabulary

**Branch**: `017-vocabulary-ipa` | **Date**: 2026-10-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/017-vocabulary-ipa/spec.md`

## Summary

Add an optional British IPA `ipa` field to vocabulary entries, show it only
once a word's answer is revealed, and fill it for all 233 existing words.

- **Model**: `VocabularyItem` gains `ipa`, which is normalised and
  validated by a small `src/lib/ipa.py`. A bad value only produces a
  warning; the word still loads.
- **Web**: the state exposes `ipa` in the same branch that already reveals
  `accepted_expressions`, so it can never leak during recall. The UI shows
  `/…/` on the reveal, sentence and feedback screens.
- **CLI**: prints `Pronunciation: /…/` after each answer.
- **Uploads**: accept an `ipa` key in Markdown files, and a `/…/` column
  in simple lists.
- **Filling the existing words**: I write a reviewed British IPA mapping,
  and a new tool (`python -m src.tools.add_ipa`) applies it. The tool:
  - checks every value against British-IPA rules;
  - backs up each file;
  - inserts only `ipa:` lines as text edits;
  - verifies nothing else changed;
  - writes a `REVIEW.md` with a 30-word spot-check sample for the user.

## Technical Context

**Language/Version**: Python 3.11+; vanilla JS, HTML and CSS

**Primary Dependencies**: existing only (Flask, PyYAML, rich); no new
dependencies

**Storage**: vocabulary Markdown files gain an optional `ipa:` line. Local
learner data (`vocabulary/`, `word-lists/`) is edited in place by the fill
tool, with backups under the gitignored `backups/`. The committed
`design/fixtures/vocabulary/` is updated too.

**Testing**: pytest (unit, contract and integration tests) and ruff

**Target Platform**: unchanged (local web server on the LAN, plus the
terminal CLI)

**Project Type**: single project

**Performance Goals**: no measurable change to loading or practice

**Constraints**:
- IPA must never appear before an answer is submitted;
- the fill must not change any other byte of the vocabulary files;
- British (RP) transcription only;
- nothing is generated automatically for later words (FR-010).

**Scale/Scope**: 233 words to fill; about 10 source files touched or added

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
|---|---|---|
| I. Test-First (NON-NEGOTIABLE) | Tests are written first and seen failing for each of these: `normalize_ipa`; `VocabularyItem.ipa` and the loader warning; the upload column and saving; `state()` exposure per step; the UI static assertions; the CLI output; and the fill tool (text-only insertion, idempotency, validation refusal, backup, verify-and-restore, review file). | ✅ Planned |
| II. Pedagogical Accuracy & Safety | **This feature adds language content (IPA), so this gate matters.** The mitigations are below the table. | ✅ Pass, with the human sample step recorded in tasks |
| III. Learner Data Privacy | Vocabulary is learner data. The fill runs locally, and backups, the mapping and the review stay in the gitignored `backups/`. Nothing is sent anywhere, and no new data is collected. | ✅ Pass |

How Principle II is covered:
- **(1) Automated checks block bad output before writing.** These cover the
  symbol inventory, stress marks and non-rhotic `r` (research R6).
- **(2) Unsure means empty.** Uncertain words are left without IPA and
  listed with a reason, never guessed (FR-006).
- **(3) A human checks a sample.** `REVIEW.md` holds a 30-word sample for
  checking against a UK learner's dictionary (SC-002).
- **(4) IPA is reference material only.** It is shown as reference text,
  never graded, and only for the learner's own words.
- **Note**: I generate the mapping from my own knowledge of the
  dictionaries. That is why steps 1 to 3 exist, and the spot check is the
  final acceptance step.

**Post-design re-check**: still passes.
- Display is gated on the existing reveal branch.
- The fill tool restores the backup automatically if its after-check
  finds any change other than the `ipa:` lines.

## Project Structure

### Documentation (this feature)

```text
specs/017-vocabulary-ipa/
├── plan.md, research.md, data-model.md, quickstart.md
├── contracts/
│   ├── ipa-field-format.md
│   ├── ipa-display-contract.md
│   └── add-ipa-tool-contract.md
├── checklists/requirements.md
└── tasks.md            # /speckit-tasks
```

### Source Code (repository root)

```text
.gitignore                         # + /backups/
src/
├── lib/ipa.py                     # NEW: normalize_ipa, display_ipa, check_british_ipa
├── models/vocabulary_item.py      # + ipa, ipa_problem; from_block reads "ipa"
├── services/
│   ├── vocabulary_loader.py       # + warning for ipa_problem
│   └── word_lists.py              # + /…/ column in simple lists; ipa in saved blocks
├── web/
│   ├── session_state.py           # state(): + "ipa" alongside accepted_expressions
│   ├── templates/index.html       # + #target-ipa; upload hint text
│   └── static/{app.js,style.css}  # render .ipa in reveal/sentence/feedback
├── cli/session.py                 # Pronunciation line; sentence prompt ipa
└── tools/
    ├── __init__.py                # NEW
    └── add_ipa.py                 # NEW: fill tool (contract add-ipa-tool-contract.md)
design/fixtures/vocabulary/sample.md   # filled with ipa (committed fixture)

tests/
├── unit/test_ipa.py                   # NEW
├── unit/test_models_vocabulary_item.py    # + ipa cases (additions)
├── unit/test_add_ipa_tool.py          # NEW
├── unit/test_session_state.py         # + ipa exposure by step (additions)
├── unit/test_web_static_assets.py     # + .ipa rendering assertions (additions)
├── unit/test_word_list_parsing.py     # + pronunciation column (additions)
├── contract/test_vocabulary_markdown_contract.py  # + ipa field (additions)
└── integration/test_ipa_flow.py       # NEW: web + CLI reveal flows, upload with IPA
```

**Structure Decision**: keep the single project. The fill tool lives in a
new `src/tools/` package, so it can be run with `python -m` and tested
like the rest of the code. The local mapping and review files live under
the gitignored `backups/`, because they contain learner word lists.

## Complexity Tracking

No constitution violations to justify.
