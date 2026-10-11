# Implementation Plan: Example Sentences Instead of Sentence Review

**Branch**: `main` (commits go straight to main) | **Date**: 2026-10-11 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/021-example-sentence/spec.md`

## Summary

The write-a-sentence step, its AI review and its voice input are removed.
Instead, after each answer the tutor shows a natural example sentence
with a Chinese translation.

- **Generation**: the local model writes the example the first time a
  word is practiced. It starts in the background while the learner is
  still recalling the word.
- **Checks**: the example must contain the word, be a single short
  sentence with a translation, and pass a content filter.
- **Saving**: examples go into the learner's own list file, or into a
  hidden examples file next to the shared words.
- **Optional practice**: a self-checked "recall the sentence" step (see
  the translation, try it, reveal, mark Got it / Not yet).

The modes become recall-only, example (the default) and example-recall.

## Technical Context

**Language/Version**: Python 3.11+; vanilla JS, HTML and CSS

**Primary Dependencies**: the existing Flask, PyYAML and requests, plus
the Ollama `/api/chat` endpoint. The optional `voice` dependency
(`faster-whisper`) is **removed**.

**Storage**:
- Own-list `.md` blocks gain `example:` and `example_zh:` keys.
- A new `.examples.json` file sits beside the shared word files.
- The progress log gains an optional `sentence_recall` field.

**Testing**: pytest, plus the real-model `eval_examples` tool with a
human review sheet.

**Target Platform**: local tutor server with browsers on the household
LAN, and the CLI

**Project Type**: single project

**Performance Goals**: an existing example shows in under 1 s. A new one
shows in 5 s or less, or the learner gets a "no example" note
(SC-001).

**Constraints**:
- fully local;
- shared `.md` files are never edited;
- old history still loads;
- removal (spec 020), IPA, part of speech and uploads are unaffected.

**Scale/Scope**: about 710 words, each with one example made on demand.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | How this plan satisfies it | Status |
|---|---|---|
| **I. Test-First** | Each new unit gets failing tests first. Tests for the removed sentence review are deleted or rewritten (justified below), and every one is listed in tasks.md. | ✅, with a justified test change |
| **II. Pedagogical Accuracy & Safety** | Each generated example passes deterministic checks before it is shown: it contains the word, is a single short sentence, has a translation, and passes a content blocklist. Naturalness and meaning are gated by a human-reviewed sample of 50 (≥ 95%, 0 unsafe) before release. | ✅ |
| **III. Learner Data Privacy** | Less data is collected than before: no sentences or voice recordings. The sentence-recall attempt text isn't stored, only the self-mark. | ✅ |

**Justified deviation**: some existing tests are edited or deleted
because the behaviour they pin, sentence review, is being removed at the
learner's request. This is recorded in Complexity Tracking.

**Post-design re-check**: ✅

## Project Structure

```text
specs/021-example-sentence/
├── plan.md, research.md, data-model.md, quickstart.md
├── contracts/practice-api.md, practice-ui.md, cli.md
└── tasks.md            # /speckit-tasks

src/
├── lib/word_forms.py          # NEW: contains_form (inflections, irregulars, phrases)
├── lib/content_filter.py      # NEW: reviewed blocklist check
├── models/vocabulary_item.py  # + example, example_zh
├── models/practice_attempt.py # + sentence_recall (sentence/feedback kept for old entries)
├── services/progress_log.py   # write/read sentence_recall
├── services/example_client.py # NEW: request_example + validate_example
├── services/examples.py       # NEW: ExampleService (stores, prepare, status, renew)
├── services/word_lists.py     # + set_example (exact block edit)
├── services/llm_client.py     # − request_correction, Judge/Teacher (keeps transport helpers)
├── services/speech_client.py  # DELETED
├── web/session_state.py       # new modes/steps; − sentence/feedback
├── web/session_registry.py    # pass ExampleService
├── web/app.py                 # + /api/sentence-recall, /api/example/new; − 4 routes
├── web/templates/index.html, static/app.js, static/style.css
├── cli/session.py, cli/__main__.py
└── tools/eval_examples.py     # NEW
tests/   (new files per task; removed-feature tests deleted/rewritten, listed in tasks.md)
```

**Structure Decision**: the existing single-project layout.

## Key Decisions

The reasoning is in [research.md](research.md).

1. There are three modes. Every example-mode answer goes through
   `reveal`, and `sentence-recall` is a new step (R1).
2. Sentence review is removed completely, while old history fields stay
   readable (R2).
3. Each example is generated, validated, and retried once (R3, R4).
4. Own lists store the example in the block. Shared words store it in a
   hidden JSON file beside them (R5).
5. Examples are prepared in the background during recall. The page polls
   for at most 6 s (R6).
6. Sentence recall is self-marked, and the attempt text isn't stored
   (R7).
7. A human-reviewed sample of 50 is the release gate (R8).

## Complexity Tracking

| Deviation | Why needed | Simpler alternative rejected because |
|---|---|---|
| Editing or deleting existing tests | The feature removes sentence review, which those tests pin | Keeping the tests would mean keeping the removed feature |
