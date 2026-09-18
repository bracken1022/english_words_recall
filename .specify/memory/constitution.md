<!--
Sync Impact Report
==================
Version change: [TEMPLATE] → 1.0.0 (initial ratification)
Modified principles: n/a (first concrete draft; all placeholders replaced)
Added sections:
  - Core Principles: I. Test-First Development (NON-NEGOTIABLE)
  - Core Principles: II. Pedagogical Accuracy & Safety
  - Core Principles: III. Learner Data Privacy
  - Additional Constraints
  - Development Workflow
  - Governance
Removed sections: none
Templates requiring follow-up:
  - .specify/templates/plan-template.md — verify Constitution Check gates reference
    the three principles above once created/updated (not modified by this command).
  - .specify/templates/tasks-template.md — verify task ordering keeps test-writing
    tasks ahead of implementation tasks per Principle I (not modified by this command).
Deferred TODOs:
  - TODO(TECH_STACK): No technology stack, hosting, or framework choices exist yet
    (repository has no application code). Additional Constraints section left generic
    until a stack is chosen; revisit on first /speckit-plan run.
-->

# AI English Tutor Constitution

## Core Principles

### I. Test-First Development (NON-NEGOTIABLE)
Tests MUST be written before implementation for every feature and bug fix. The
sequence is: write tests → get them reviewed/approved → confirm they fail for the
right reason → implement until they pass → refactor. No implementation task may be
started until its corresponding test task exists and has been reviewed.
Rationale: For a tutoring product, regressions silently produce wrong language
feedback to learners. Enforcing red-green-refactor is the cheapest guardrail against
that class of error, and it is non-negotiable because the cost of skipping it only
shows up later, in learner-facing mistakes.

### II. Pedagogical Accuracy & Safety
Any feature that generates, corrects, scores, or explains English language content
(grammar, vocabulary, pronunciation, writing feedback, conversation practice) MUST
have an explicit correctness check before it ships: either a reviewed test suite of
known-correct/known-incorrect examples, a human pedagogical review, or both for
higher-risk features (e.g., grading, certification-adjacent scoring). Generated
content MUST NOT present uncertain or unverified language judgments as authoritative
without flagging the uncertainty to the learner. Content MUST be filtered for
harmful, offensive, or age-inappropriate material before being shown to a learner.
Rationale: The product's entire value is trustworthy language feedback; an app that
teaches wrong grammar or unsafe content as confidently as correct grammar breaks
that trust and can actively harm a learner's progress.

### III. Learner Data Privacy
Learner-identifying data (voice recordings, written submissions, progress history,
contact info) MUST be collected only when needed for the feature at hand, stored
with access limited to what that feature requires, and never used for purposes the
learner wasn't told about (e.g., model training, analytics, third-party sharing)
without explicit, separate consent. Any feature handling learner data MUST document
what is collected and why in its spec before implementation begins.
Rationale: Language-learning data (recordings of a learner's voice, their mistakes,
sometimes minors' data) is sensitive; treating it casually creates legal exposure
and undermines learner trust in the tutor.

## Additional Constraints

TODO(TECH_STACK): No technology stack, hosting platform, or third-party AI provider
has been chosen yet — this repository currently contains no application code.
Once a stack is selected (e.g., during the first `/speckit-plan` run), amend this
section with concrete constraints (supported platforms, required AI provider(s),
performance/latency budgets for real-time conversation practice, accessibility
requirements, and offline/low-bandwidth behavior if applicable).

## Development Workflow

- Every change proposed via a feature spec MUST show how it satisfies Principles I–III
  before implementation starts (test plan, accuracy/safety check, data-handling note).
- Code review MUST verify: tests exist and were written before the implementation they
  cover, any new language-generation or scoring logic has a correctness check, and any
  new data collection is documented and minimized.
- Complexity that bypasses these principles (e.g., "we'll add tests later," "we'll
  clarify data use later") MUST be called out explicitly and justified in the spec's
  plan, not silently merged.

## Governance

This constitution supersedes other informal practices for this project. Amendments
require: (1) a documented rationale for the change, (2) a version bump following
semantic versioning (MAJOR for incompatible principle removals/redefinitions, MINOR
for new principles or materially expanded guidance, PATCH for wording/clarification
only), and (3) an updated Sync Impact Report at the top of this file describing what
changed. All specs, plans, and task lists produced by Spec Kit commands MUST be
checked against these principles; any deviation must be justified in that artifact's
own documentation rather than silently ignored. Use this file as the source of truth
for runtime development guidance until a separate guidance file is introduced.

**Version**: 1.0.0 | **Ratified**: 2026-09-18 | **Last Amended**: 2026-09-18
