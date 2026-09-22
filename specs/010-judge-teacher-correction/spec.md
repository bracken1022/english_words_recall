# Feature Specification: Split Sentence Review into Judge and Teacher Roles

**Feature Branch**: `010-judge-teacher-correction`

**Created**: 2026-09-22

**Status**: Draft

**Input**: User description: "Split the sentence-correction call into two roles against the same local qwen3:14b model: a Judge role that checks grammar correctness, target-word usage, and naturalness, and a Teacher role that explains the mistake and gives a natural rewrite, only invoked when the Judge finds a problem. This is a refactor for clearer/more focused prompts, not a speed optimization — the existing CorrectionResult shape and everything downstream (session state, tests, UI) must stay unchanged."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - One focused job per prompt (Priority: P1)

The person maintaining this tutor's correction prompts currently has one
prompt asking the local model to do four different jobs at once (check
grammar, check target-word usage, judge naturalness, and — if needed —
write an explanation and a corrected sentence). They want that split into
two clearly separated roles: a **Judge** that only checks correctness/
usage/naturalness, and a **Teacher** that only explains and rewrites,
called just when the Judge found something wrong — so each prompt can be
read, tested, and improved on its own.

**Why this priority**: This is the entire ask — everything else in this
feature exists to make this split safe to ship without changing what the
learner experiences.

**Independent Test**: Can be tested by reviewing the Judge prompt and the
Teacher prompt separately against their own small set of example
sentences, confirming each does only its own job.

**Acceptance Scenarios**:

1. **Given** a sentence that is already correct and natural, **When** it is
   reviewed, **Then** only the Judge role is invoked — no explanation or
   rewrite is requested from the model at all.
2. **Given** a sentence with a grammar or naturalness problem, **When** it
   is reviewed, **Then** the Judge role runs first, finds the problem, and
   only then is the Teacher role invoked to produce an explanation and a
   corrected sentence.
3. **Given** a sentence that doesn't use the target expression, **When**
   it is reviewed, **Then** the Judge reports that regardless of whether
   the sentence is otherwise grammatically fine, matching today's
   behavior of treating target-usage and correctness as independent
   findings.

---

### User Story 2 - Nothing else changes (Priority: P2)

Everyone else who depends on sentence review today — the practice-session
flow, the existing automated tests, and the web UI — must keep working
exactly as it does now, with no code changes required on their part.

**Why this priority**: This is what makes the split a safe refactor rather
than a rewrite; it depends on User Story 1's split existing first, so it's
verified second.

**Independent Test**: Run the existing automated test suite unmodified and
confirm every test that exercises sentence review still passes, with no
new fields appearing in what those tests observe.

**Acceptance Scenarios**:

1. **Given** the existing practice flow (recall a word, write a sentence,
   see feedback), **When** a sentence is reviewed under the new two-role
   split, **Then** the learner sees the exact same kinds of feedback
   messages as before, with no new or missing case.
2. **Given** the existing automated test suite, **When** it is run against
   the two-role split, **Then** every previously-passing test still
   passes without modification.

### Edge Cases

- What happens if the Judge can't be reached or its reply can't be used?
  Reported as "review unavailable," exactly as any failure is today.
- What happens if the Judge succeeds and finds a problem, but the Teacher
  then can't be reached or its reply can't be used? The whole review is
  reported as "review unavailable" rather than a half-finished result —
  today's result never has a "problem found but no explanation" state, and
  this feature must not invent one.
- What happens when the sentence doesn't use the target expression but is
  otherwise grammatically fine, or vice versa? Both findings are reported
  independently, exactly as they are today.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST evaluate a submitted sentence's grammar
  correctness, target-expression usage, and naturalness through a
  distinct "Judge" request to the local model, separate from any request
  that produces an explanation or a rewrite.
- **FR-002**: The system MUST only make a "Teacher" request (to produce an
  explanation and a natural rewrite) when the Judge found a grammar or
  naturalness problem — it MUST NOT request an explanation or rewrite for
  a sentence the Judge found acceptable.
- **FR-003**: The system MUST continue to report exactly the same
  judgment information it does today — whether the target expression was
  used, whether correction is needed, the corrected sentence, and the
  explanation — in the same combined shape every existing caller already
  reads; no field is added, removed, or renamed.
- **FR-004**: The system MUST report "review unavailable" (matching
  today's existing behavior for any failure) whenever the Judge request
  fails or its reply can't be used.
- **FR-005**: The system MUST also report "review unavailable" whenever
  the Judge found a problem but the subsequent Teacher request fails or
  its reply can't be used — never a partial result.
- **FR-006**: The system MUST use the same local model and connection
  settings for both the Judge and the Teacher requests; no new
  configuration is introduced for this feature.
- **FR-007**: This change MUST NOT alter anything the learner sees or
  anything the rest of the app depends on — the practice flow, the
  feedback wording, and the "reviewing" waiting indicator all remain
  exactly as they are today.
- **FR-008**: Per this project's existing rule that any change to
  language-judgment logic have an explicit correctness check before it
  ships, this change MUST be validated against a reviewed set of
  known-correct and known-incorrect example sentences before being
  considered complete.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of existing automated tests that exercise sentence
  review continue to pass unmodified after this change.
- **SC-002**: For a reviewed set of known-correct example sentences, the
  two-role pipeline reports "no correction needed" at least as reliably as
  today's single-request pipeline, and never requests an explanation/
  rewrite for any of them.
- **SC-003**: For a reviewed set of known-incorrect example sentences, the
  two-role pipeline reports "correction needed" with a usable corrected
  sentence and explanation at least as reliably as today's single-request
  pipeline.
- **SC-004**: The Judge's and the Teacher's own prompts can each be
  reviewed and evaluated against their own dedicated example sentences,
  independent of one another — the thing this feature exists to make
  possible.

## Assumptions

- Grammar and naturalness problems both continue to roll up into the same
  single "needs correction" signal already exposed today — this feature
  does not split that into separate grammar/naturalness fields, since the
  existing result shape must stay unchanged (FR-003).
- Whether the Teacher is invoked depends only on "needs correction";
  whether the target expression was used is reported independently and
  does not by itself trigger or suppress the Teacher request — matching
  how these two findings are already independent of each other today.
- This is a backend-only change to the sentence-review service
  (`src/services/llm_client.py`); the CLI, the practice-session state
  machine, and the web UI require no changes and are not touched.
- This feature is explicitly not a performance optimization (per the
  request that prompted it) — it is not expected to reliably speed up or
  slow down review responses, and no speed target is set. A genuine speed
  improvement (e.g., a smaller/faster model for the Judge role) is a
  separate, future consideration, not part of this feature.
