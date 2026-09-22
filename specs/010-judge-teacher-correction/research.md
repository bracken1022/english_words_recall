# Research: Split Sentence Review into Judge and Teacher Roles

No open `NEEDS CLARIFICATION` markers — spec.md's Assumptions already
resolved every open design question. This file records the remaining
implementation-shape decisions and the alternatives considered.

## 1. How grammar/naturalness/usage map onto today's fields

**Decision**: The Judge's response schema asks for three independent
booleans: `uses_expression`, `grammatically_correct`, `natural`.
`request_correction()` derives `needs_correction = not
(grammatically_correct and natural)` — collapsing two Judge-level checks
into the one `needs_correction` field `CorrectionResult` already exposes,
exactly as spec.md's Assumptions require. `uses_expression` passes through
unchanged, independent of the other two (matching today's independence
between usage and correctness).

**Rationale**: This is the only mapping that satisfies FR-003 (no new
field) while still giving the Judge role its own, single-purpose schema
per FR-001 — the three-way check the user asked for exists at the prompt/
schema level, and collapses to the two-way signal the rest of the app
already understands only at the boundary between `_request_judge()` and
`request_correction()`.

**Alternatives considered**:
- **Expose `grammatically_correct`/`natural` separately on
  `CorrectionResult`** — rejected outright by spec.md FR-003; would also
  require changes to `app.js`'s `renderFeedback()` and the progress-log
  feedback string, which this feature explicitly must not touch.

## 2. Request/response shape for each role

**Decision**:

- **Judge** — system prompt: "You are an English grammar and naturalness
  judge for a language learner. Respond only with the requested JSON
  object." Response format:
  ```json
  {
    "type": "object",
    "properties": {
      "uses_expression": {"type": "boolean"},
      "grammatically_correct": {"type": "boolean"},
      "natural": {"type": "boolean"}
    },
    "required": ["uses_expression", "grammatically_correct", "natural"]
  }
  ```
  User message: target expression + sentence, asking all three questions
  directly — no mention of corrections or explanations at all.

- **Teacher** — system prompt: "You are an English writing teacher
  helping a language learner fix a mistake in their sentence. Respond
  only with the requested JSON object." Response format:
  ```json
  {
    "type": "object",
    "properties": {
      "corrected": {"type": "string"},
      "explanation": {"type": "string"}
    },
    "required": ["corrected", "explanation"]
  }
  ```
  User message: target expression + the original sentence + "This
  sentence has a grammar or naturalness problem" (i.e., it's only ever
  called once the Judge has already established that), asking for a
  corrected, natural version and a one-to-two sentence explanation.

**Rationale**: Each schema only asks for what that role decides — the
Judge is never asked to write anything, and the Teacher is never asked to
re-judge anything it's already told is true. This is the actual "clearer,
more focused prompt" the feature exists to produce (spec.md User Story 1).

**Alternatives considered**:
- **One shared schema/prompt with optional fields depending on role** —
  rejected: keeping two fully separate constants (prompt + schema pairs)
  is what makes each role independently reviewable/testable (spec.md
  SC-004), which a single parameterized prompt would undermine.

## 3. Rewriting `test_ollama_correction_contract.py`

**Decision**: This file is rewritten, not left alone — every existing
test in it asserts a single `requests.post` call carrying all four fields
in one JSON schema, which is no longer how the wire protocol works. The
rewrite mocks `requests.post` with `side_effect=[judge_response,
teacher_response]` for the two-call path, or a single response for the
Judge-only path, and inspects `mock_post.call_args_list` (both calls)
instead of `call_args` (the last call only). Every existing *observable
guarantee* it protects — a connection error, non-200, malformed JSON, or
a wrong-typed field is always treated as `available=False` — is
preserved, just re-expressed against two calls, each with its own schema.

**Reconciling this with spec.md's SC-001** ("100% of existing automated
tests... continue to pass unmodified"): that success criterion is about
*callers of* `request_correction()` — `test_session_state.py` (which
injects `CorrectionResult` directly via `correction_fn`, never touching
`requests.post`), and every web-layer test (which patches
`request_correction` itself as an opaque function). None of those change.
`test_ollama_correction_contract.py` is different in kind: it is the test
suite *for* `llm_client.py`'s own internals, which this feature is
explicitly changing on purpose — rewriting it is the point of Test-First
Development here (Constitution Principle I), not a violation of SC-001.

**Alternatives considered**:
- **Keep the old tests passing by preserving a single combined call
  internally, and only split prompts cosmetically** — rejected: this
  wouldn't actually implement FR-001/FR-002 (a real, separate Judge
  request that gates whether a Teacher request happens at all), just
  rename things.

## 4. The Principle II correctness check (FR-008)

**Decision**: A small, hand-curated table of example sentences (paired
with the target expression and the expected Judge/Teacher outcome —
already-correct, grammar problem, unnatural phrasing, missing target
expression, and at least one sentence combining two of these) is recorded
in `quickstart.md`, to be run manually against a live local Ollama server
with `qwen3:14b` before this feature is considered done — comparing the
new two-call pipeline's output for each example against the expected
outcome (and, where practical, against what today's single-call pipeline
already produces for the same sentence, as a direct before/after check).

**Rationale**: This is the **first** feature built since the constitution
was ratified that changes language-judgment logic — there is no existing
"reviewed known-correct/known-incorrect examples" fixture anywhere in
this project to extend. Ollama's actual judgment quality isn't something
an automated, mocked unit test can verify (mocks only prove the *plumbing*
around a canned reply is correct, which `test_ollama_correction_contract.py`
already covers) — this project has consistently treated live-model
behavior as a manual verification concern (e.g. the loading-indicator
work), and this establishes the same pattern for correctness review going
forward.

**Alternatives considered**:
- **An automated test that calls a real, live Ollama instance** —
  rejected: no CI environment here is guaranteed to have Ollama running
  with `qwen3:14b` pulled, and language-quality judgments aren't a
  deterministic assertion regardless (the same prompt can reasonably
  produce slightly different wording across runs) — a human reviewing
  the outcomes against expectations is the actual correctness check,
  matching Principle II's own wording ("a reviewed test suite... a human
  pedagogical review, or both").
