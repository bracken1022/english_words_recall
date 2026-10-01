# Implementation Plan: Reference-Driven UI Design Workflow

**Branch**: `014-reference-driven-ui` | **Date**: 2026-10-01 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/014-reference-driven-ui/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

This feature delivers a *workflow*, not a page redesign. It has three parts:

1. **The skill**: `.claude/skills/frontend-design/SKILL.md`, which exists but is empty. It is
   filled in with a page-independent methodology (inspect references → read the existing
   UI → write a design interpretation → implement inside the existing Flask/Jinja +
   vanilla CSS/JS stack → verify with screenshots → refine, at most 3 passes → report).
   It also holds English Tutor-wide learning UI rules, an accessibility floor, and an
   explicit "do not copy" list. Long reference material, such as the analysis checklist,
   the interpretation template and the verification recipe, goes in sibling files under
   `.claude/skills/frontend-design/` so `SKILL.md` stays short. Page-specific requirements
   come from the developer's request, never from the skill.
2. **Reference storage**: `design/references/{vocabulary-practice,sentence-practice,progress,shared}/`,
   each kept in git with a `.gitkeep`, plus `design/README.md` stating what belongs there
   and what doesn't. It also adds a small fixture vocabulary at
   `design/fixtures/vocabulary/` so verification runs never touch the learner's real
   `vocabulary/` or `progress.md`. Screenshots go to `design/verification/`, which is
   git-ignored.
3. **Verification recipe**: a documented way to start the app on a spare port against
   the fixture vocabulary, drive it into each UI state through the existing JSON API
   (the session lives on the server, so a page reload shows whatever state the API
   produced), and take screenshots at 1280px and 390px. It uses whichever browser
   tooling the session has, in this order: Claude browser/Chrome tools, then
   `npx playwright screenshot`, then a plain "verification skipped" notice.

No application code changes. Tests protect the runtime boundary (nothing in `src/`
refers to `design/`, and the app serves `/` with no `design/` folder present), plus the
skill and reference-folder structure contracts.

## Technical Context

**Language/Version**: Markdown (skill and docs). Python 3.11+ for the new pytest tests.
The app under redesign is Flask + Jinja2 templates + vanilla CSS/JS (`src/web/`).

**Primary Dependencies**: None new for the project. Visual verification optionally uses
tools that live outside the repo: the Claude in Chrome / built-in browser MCP tools, or
`npx playwright` (fetched on demand by npx, never added to `pyproject.toml`).

**Storage**: Files only. Reference images under `design/references/` (committed, at the
developer's discretion). Screenshots under `design/verification/` (git-ignored).

**Testing**: pytest, following the existing static-content convention in
`tests/unit/test_web_static_assets.py`: structural assertions on shipped files, no JS
test runner. Visual quality is checked by the workflow's screenshots, not by automated
tests (a visual regression platform is out of scope).

**Target Platform**: Developer machine running Claude Code (macOS here). The verified app
runs locally with `python -m src.web`.

**Project Type**: Single project. Adds a dev-time skill and design assets beside the
existing `src/web` app.

**Performance Goals**: N/A. The only bound is the refine loop: at most 3 passes (FR-019).

**Constraints**:
- `design/` MUST NOT be referenced by anything under `src/` (FR-003, SC-004).
- No learner data in verification runs: use the fixture vocabulary and a throwaway
  progress file.
- The skill MUST NOT name a specific page in its rules (FR-007). Page names appear
  only as examples of folder names.
- No new runtime or dev dependencies in `pyproject.toml` (FR-008).

**Scale/Scope**: 1 skill (about 150 lines plus 3 reference files), 4 reference folders,
1 fixture vocabulary file, about 8 new tests. The existing UI is 3 files (~880 lines),
which this feature does not change.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Assessment | Status |
|-----------|-----------|--------|
| I. Test-First | New tests (runtime independence, folder contract, skill contract) are written first and fail before the skill/folders exist. The existing suite is the regression guard for "behavior unchanged" in later redesigns, and the skill requires running it before and after any redesign. | PASS |
| II. Pedagogical Accuracy & Safety | No language content is generated, corrected or scored. The skill forbids changing answer checking, feedback wording semantics or flow. Correct/incorrect distinction is a mandatory UI rule. | PASS (not engaged) |
| III. Learner Data Privacy | Verification uses `design/fixtures/vocabulary/` and a throwaway progress file, so the learner's `vocabulary/` and `progress.md` are never read or written. Screenshots contain fixture words only and are git-ignored. | PASS |

**Post-design re-check (after Phase 1)**: still PASS. The design added only Markdown, a
fixture file, `.gitignore` entries and tests, and introduced no runtime code paths or
data collection.

## Project Structure

### Documentation (this feature)

```text
specs/014-reference-driven-ui/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   ├── skill-contract.md            # What SKILL.md must contain / must not contain
│   ├── reference-folder-contract.md # design/ layout and runtime boundary
│   └── verification-recipe.md       # Start app, drive states, screenshot, compare
└── tasks.md             # Phase 2 output (/speckit-tasks, not created here)
```

### Source Code (repository root)

```text
.claude/skills/frontend-design/
├── SKILL.md                    # Methodology + learning UI rules (filled in; currently empty)
├── reference-analysis.md       # Analysis checklist (layout … responsive behavior)
├── design-interpretation.md    # Interpretation template (7 topics + "not carried over")
└── visual-verification.md      # Tooling ladder, state-driving recipe, compare checklist, report format

design/
├── README.md                   # What goes here, what never does, runtime boundary
├── references/
│   ├── vocabulary-practice/.gitkeep
│   ├── sentence-practice/.gitkeep
│   ├── progress/.gitkeep
│   └── shared/.gitkeep
├── fixtures/
│   └── vocabulary/sample.md    # Small fixture word set for verification runs
└── verification/               # Screenshots (git-ignored)

.gitignore                      # + /design/verification/

tests/unit/
├── test_design_workflow_skill.py      # Skill contract assertions
└── test_design_reference_layout.py    # Folder contract + runtime boundary

src/web/                        # UNCHANGED by this feature
```

**Structure Decision**: Single project. Dev-time assets live at the repo root under
`design/` and `.claude/skills/`, both outside the `src*` package that setuptools ships,
so they cannot leak into the runtime. Tests sit in `tests/unit/` with the existing
static-asset tests.

## Complexity Tracking

No constitution violations. Nothing to justify.
