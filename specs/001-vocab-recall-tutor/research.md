# Phase 0 Research: Vocabulary Recall Tutor

All Technical Context choices below were confirmed with the user before this
research was written (interface, language, LLM access method); the remaining
decisions are this feature's own design choices, made because the spec leaves
them as implementation details.

## Interface: Terminal / CLI

- **Decision**: A plain interactive CLI loop (`src/cli/session.py`), optionally
  styled with `rich` for readable output (colored correct/incorrect, formatted
  diff between the learner's sentence and the corrected one).
- **Rationale**: Confirmed with user as fastest to build for a personal local
  tool; no browser or GUI toolkit dependency; matches "runs entirely on my own
  machine" framing of the feature.
- **Alternatives considered**: Local web app (nicer text editing, but adds a
  server + browser dependency for no functional gain here); desktop GUI (more
  polish, much more implementation surface for a single-learner tool).

## Language/Runtime: Python 3.11+

- **Decision**: Python 3.11+, standard library plus a small dependency set.
- **Rationale**: Confirmed with user; strong ecosystem for local-LLM HTTP
  clients, trivial file/Markdown I/O, no build/compile step, and `pytest` gives
  the test-first workflow the constitution requires with minimal ceremony.
- **Alternatives considered**: TypeScript/Node (better fit if a web UI were
  chosen, not needed here).

## Local LLM access: Ollama HTTP API

- **Decision**: Call a locally running Ollama server's chat endpoint
  (`POST http://localhost:11434/api/chat`) with the learner's sentence and the
  target expression in the prompt; parse the model's reply for a
  correct/needs-correction judgment, a corrected sentence (if any), and a short
  explanation. The default model is `qwen3:14b`; the model name is always a
  configurable value (CLI `--model` flag / `llm_client.py` parameter), never
  hardcoded past the default.
- **Rationale**: Confirmed with user; Ollama is the most common way to run open
  local models today and exposes a simple HTTP contract, which keeps FR-007/FR-010
  (send for review; degrade gracefully if unavailable) straightforward: any
  connection error or non-200 response is treated as "correction unavailable."
  `qwen3:14b` is a capable general-purpose local model with good instruction-
  following for structured output, a reasonable choice as a default without
  locking the learner into it.
- **Alternatives considered**: A generic OpenAI-compatible `/v1/chat/completions`
  endpoint (would also work, and Ollama exposes an OpenAI-compatible route too,
  but targeting Ollama's native API directly is simpler for a single named
  runtime and avoids adding an abstraction layer with only one implementation);
  shelling out to the `ollama` CLI binary (rejected — the requirement is
  explicit that the app is an HTTP client of the Ollama API, not a subprocess
  wrapper around its CLI, which would also make structured-output requests and
  error handling far more brittle to parse from stdout/stderr).

## Prompting & response parsing for grammar/naturalness correction

- **Decision**: Request **structured data** directly, using Ollama's
  `format` parameter with a JSON Schema describing the four required fields
  (`uses_expression: bool`, `needs_correction: bool`,
  `corrected: string|null`, `explanation: string|null`). Ollama constrains
  the model's decoding to that schema, and `message.content` comes back as a
  JSON string, which `llm_client.py` parses with the standard library `json`
  module. Any reply that isn't valid JSON, or that parses but is missing a
  required key, is treated identically to "LLM unavailable" per FR-010 —
  never partially trusted or shown to the learner.
- **Rationale**: The requirement is explicit that sentence review must
  return structured data, not free text. Ollama's schema-constrained
  generation is the most reliable way to get that from a local model — far
  more consistent than asking a model to emit labeled text lines and hoping
  it complies — while the defensive JSON-parse-and-validate step still keeps
  FR-010's "malformed output degrades safely" guarantee for any model that
  doesn't honor the schema, or for a schema-supporting model that emits a
  key with an unexpected type.
- **Alternatives considered**: The originally-planned labeled-line format
  (`USES_EXPRESSION: yes\nNEEDS_CORRECTION: yes\n...`) — superseded by this
  decision; it worked but was strictly a workaround for the lack of a
  structured-output request, which Ollama supports directly. Requesting
  plain unconstrained JSON via prompt instructions alone (no `format`
  schema) — rejected as the primary path for the same reason labeled lines
  were: local models are not reliably consistent about it without
  schema-constrained decoding.

## Determinism of the learning state machine

- **Decision**: `CorrectionResult` (Ollama's structured reply) is treated as
  an opaque payload that only ever gets *displayed* and *logged* — attached
  verbatim to a `PracticeAttempt`'s `sentence`/`feedback` fields. Nothing in
  `session.py`'s control flow (which item is next, whether an item repeats,
  whether a session ends, how `matcher.py` grades recall) reads or branches
  on any field of `CorrectionResult`. Recall grading is exact-string matching
  against `VocabularyItem` data only (FR-004); progression is strictly
  forward through the filtered item list only (FR-016); none of it depends
  on Ollama being installed, reachable, or returning any particular content.
- **Rationale**: The requirement is explicit — Ollama evaluates language
  quality and must not control lesson progression. Keeping the state machine
  a pure function of `VocabularyItem`/`PracticeAttempt` data (not of LLM
  output) is also what makes it deterministic and unit-testable without a
  model running at all, which the existing test suite already demonstrates
  (`tests/integration/test_recall_flow.py` passes with zero LLM interaction).
- **Alternatives considered**: Letting `needs_correction` influence whether
  an item is repeated later in the session (e.g., a lightweight
  "resurface if the sentence needed correction" rule) — rejected as
  out-of-scope scope creep: the spec's Assumptions already defer any
  spaced-repetition-style scheduling, and doing this would make session
  behavior depend on a third-party model's variable output, breaking
  determinism for a feature nobody asked for in this iteration.

## Validating correction quality (Constitution Principle II)

- **Decision**: A fixture set of representative example sentences — some
  already correct/natural, some with clear grammar errors, some technically
  grammatical but unnatural — paired with their target expression, used in
  contract tests to assert the pipeline correctly classifies "needs correction"
  vs. "already fine" and that a malformed/empty model reply is handled per
  FR-010. This checks the *pipeline's* handling of LLM output, not the LLM's own
  linguistic judgment (which is outside this project's control).
- **Rationale**: Satisfies the constitution's requirement that any
  language-judging feature have an explicit correctness check before shipping,
  without pretending the app can guarantee a third-party model's grammatical
  accuracy.
- **Alternatives considered**: Human pedagogical review only — kept as a
  complement, not a replacement, since it doesn't run in CI.

## Vocabulary Markdown format

- **Decision**: A vocabulary Markdown file contains one or more items, each as
  a `---`-delimited YAML block (frontmatter-style, repeated within the file):

  ```markdown
  ---
  english: receive
  alternates: [accept]
  chinese: 收到；接受
  group: unit1
  ---
  ```

  `vocabulary_loader.py` parses each block independently with `PyYAML`; a block
  that fails to parse or is missing `english`/`chinese` is skipped and reported
  per FR-013, without aborting the rest of the file.
- **Rationale**: Keeps the file genuinely Markdown and hand-editable (per
  SC-002/SC-003) while giving structured fields a simple existing syntax
  (YAML) instead of inventing a bespoke format; per-block isolation is exactly
  what FR-013's "skip the bad entry, keep the rest" requires.
- **Alternatives considered**: A Markdown table (harder to extend with a
  variable number of alternates per row); one item per file (works, but forces
  a lesson/group into a directory-naming convention instead of a `group` field).

## Progress log Markdown format

- **Decision**: A single append-only `progress.md`, where each practice attempt
  is appended as its own `---`-delimited YAML block (same parsing helper as
  vocabulary files) with `timestamp`, `item`, `answer`, `correct`, `sentence`,
  and `feedback` fields.
- **Rationale**: Reuses the same block-parsing convention as vocabulary files
  (one shared `lib/markdown_blocks.py`), keeps every attempt in one place for
  SC-005 ("determine, for any past attempt, ... without consulting the app"),
  and appending is a trivial, corruption-resistant write pattern for a
  single-writer local tool.
- **Alternatives considered**: One file per day/session (avoids one growing
  file, but the spec's Assumptions already accept unbounded growth and SC-005
  is easier to satisfy from a single file); a narrative prose log instead of
  structured blocks (harder to keep unambiguous and testable).

## Testing strategy

- **Decision**: `pytest` throughout. Contract tests mock the Ollama HTTP call
  (no real model required in CI) and assert the request/response contract in
  `contracts/`. Unit tests cover `matcher.py` (exact-match grading rules),
  `markdown_blocks.py` (parsing, malformed-block handling), and
  `progress_log.py` (append/read round-trip). Integration tests drive
  `cli/session.py` end-to-end with simulated stdin/stdout for the primary
  flows (correct recall, incorrect recall, sentence correction, LLM
  unavailable, empty vocabulary set).
- **Rationale**: Matches Constitution Principle I (tests before implementation)
  and gives each layer (parsing, grading, LLM integration, session flow) an
  independently testable seam, mirroring the spec's three independently
  testable user stories.
- **Alternatives considered**: Testing only at the CLI/integration level —
  rejected because it would make LLM-unavailable and malformed-entry edge
  cases slow/flaky to cover without unit-level mocking.
