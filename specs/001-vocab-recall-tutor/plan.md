# Implementation Plan: Vocabulary Recall Tutor

**Branch**: `001-vocab-recall-tutor` | **Date**: 2026-09-18 (amended 2026-09-18: Ollama runtime specifics) | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-vocab-recall-tutor/spec.md`

## Summary

A local, single-learner CLI tool that drills English vocabulary for Chinese
speakers: it shows a Chinese meaning, has the learner recall the English
expression (exact-match graded), has them write an original sentence with it, and
sends that sentence to a locally running Ollama model (default `qwen3:14b`,
configurable) for grammar/naturalness correction via Ollama's HTTP API. All
vocabulary content and practice history are plain Markdown files on disk —
there is no database. The LLM's role is strictly advisory: it evaluates
language quality and nothing else — the learning state machine (grading,
item ordering, session progression) is deterministic and computed entirely
independently of anything Ollama returns.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: `requests` for the Ollama HTTP API (never the `ollama`
CLI binary — the app is an HTTP client only), `PyYAML` for parsing the
frontmatter-style blocks in vocabulary/progress Markdown files, the standard
library `json` module for parsing Ollama's structured sentence-review output,
`rich` for readable terminal output, `pytest` for tests

**Storage**: Plain Markdown files on the local filesystem — vocabulary files
(learner/author-edited) and an append-only progress log; no database

**Testing**: `pytest`, with HTTP calls to Ollama mocked in contract/unit tests and
real end-to-end flows exercised in integration tests via simulated stdin/stdout

**Target Platform**: Cross-platform terminal (developed/verified on macOS; no
platform-specific APIs used) — runs entirely on the learner's own machine

**Project Type**: Single project — command-line application

**Performance Goals**: Non-LLM operations (loading vocabulary, matching, writing
the progress log) complete well under 200ms so the app never feels like the
bottleneck; grammar-correction latency is bounded by the local LLM itself, which
is outside this feature's control

**Constraints**: Fully offline except for the loopback call to the local Ollama
server; no database engine or remote service may be introduced; vocabulary and
progress data must remain plain-text Markdown readable without the app. The
app MUST call Ollama's HTTP API (never spawn the `ollama` CLI as a
subprocess). Sentence-review requests MUST use Ollama's structured-output
(`format` JSON-schema) parameter and be parsed as structured data, not
free-text labels; a non-200 response, connection failure, or a reply that
fails to parse/validate against the schema MUST all be treated identically as
"correction unavailable" (FR-010) — never shown to the learner as partial or
guessed output. The default model is `qwen3:14b`; the model name MUST be
operator-configurable (CLI flag), not hardcoded. Ollama's output MUST be
treated purely as an opaque evaluation payload: session control flow (grading
via `matcher.py`, forward-only item progression, lesson/tag filtering) MUST
be computed solely from `VocabularyItem`/`PracticeAttempt` data and MUST NOT
branch on anything the LLM returns — the learning state machine stays
deterministic and testable without Ollama running at all (proven by
`tests/integration/test_recall_flow.py` already passing with no mock LLM
involved).

**Scale/Scope**: Single learner, single machine, no concurrency; vocabulary sets
realistically range from tens to a few thousand items

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| I. Test-First Development | Plan's project structure carves out `tests/{contract,integration,unit}` up front; `/speckit-tasks` will order test-writing tasks before the implementation tasks they cover. | PASS |
| II. Pedagogical Accuracy & Safety | The sentence-correction feature is the one place this project generates/judges language content. Phase 0 research defines how the LLM call is validated (a fixture set of known correct/incorrect example sentences used in contract tests) and how an unavailable/malformed/schema-invalid LLM response degrades safely (already required by FR-010; no unflagged authoritative claims are shown when the LLM is down). Ollama is scoped to language evaluation only — it never decides grading or progression — so a bad or malicious model response can at worst produce misleading *feedback text*, never an incorrect *grade* or a corrupted session flow. | PASS |
| III. Learner Data Privacy | All learner data (recall answers, sentences, feedback, timestamps) stays in local Markdown files and is only ever sent to the learner's own local LLM over loopback — never to a third party, never for training. This matches the spec's Assumptions (single-machine, no network sync). | PASS |

No violations to justify; **Complexity Tracking** is not needed for this feature.

**Post-Phase 1 re-check**: `data-model.md` and `contracts/` add no database,
no third-party network calls, and no new language-generation surface beyond
the sentence-correction call already covered above — all three gates still
PASS after design.

**Re-check after this amendment** (switching the correction call to Ollama's
structured `format` output, pinning the default model to `qwen3:14b`, and
making the state-machine/LLM boundary explicit): no new gate is introduced
and no existing gate is weakened — Principle II's check is strengthened
(schema-invalid replies are now an explicit, testable failure mode, not just
"malformed"), and the determinism requirement is a stricter, not looser,
version of what the original design already did in practice. Still PASS.

## Project Structure

### Documentation (this feature)

```text
specs/001-vocab-recall-tutor/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/
├── models/         # VocabularyItem, PracticeAttempt — plain dataclasses, no ORM
├── services/
│   ├── vocabulary_loader.py   # reads/parses vocabulary Markdown files, applies lesson/tag filter
│   ├── matcher.py             # exact-match grading against a vocabulary item's accepted expressions
│   ├── llm_client.py          # Ollama HTTP client: POSTs /api/chat with a JSON-schema `format`,
│   │                          # parses the structured reply into CorrectionResult (never CLI-spawned)
│   └── progress_log.py        # appends/reads practice attempts as Markdown blocks
├── cli/
│   └── session.py             # the interactive recall -> sentence -> correction loop
└── lib/
    └── markdown_blocks.py     # shared parsing of the "---"-delimited YAML-in-Markdown blocks

tests/
├── contract/    # Ollama request/response contract (mocked HTTP), vocab/progress Markdown format contracts
├── integration/ # full CLI session flows (recall, sentence+correction, LLM-unavailable, malformed vocab entry)
└── unit/        # matcher grading rules, markdown_blocks parsing, progress_log formatting
```

**Structure Decision**: Single-project CLI layout (Option 1 from the template).
There is no frontend/backend split and no mobile/API split — the entire feature is
one local command-line application, so `src/{models,services,cli,lib}` plus a
matching `tests/{contract,integration,unit}` tree is sufficient.

## Complexity Tracking

*No Constitution Check violations — this section is intentionally empty.*
