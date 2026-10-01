# Tasks: Reference-Driven UI Design Workflow

**Input**: Design documents from `/specs/014-reference-driven-ui/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included. Constitution Principle I (Test-First) is non-negotiable. Each story's
contract tests are written first and must FAIL before the matching content is written.
Tests are static-content assertions, following the convention in
`tests/unit/test_web_static_assets.py`.

**Organization**: Grouped by user story. This feature changes no application code under
`src/`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story the task belongs to (US1–US4)

## Path Conventions

Repo root: `.claude/skills/frontend-design/` (skill), `design/` (dev-time assets),
`tests/unit/` (new tests). `src/web/` is read-only for this feature.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Record the baseline and create the empty directory skeleton.

- [X] T001 Run `pytest -q` from the repo root and record the pass count as the baseline in `specs/014-reference-driven-ui/tasks.md` Notes. Note any pre-existing failures, such as from the uncommitted `src/services/llm_client.py` / `tests/contract/test_ollama_correction_contract.py` changes, so they aren't blamed on this feature.
- [X] T002 [P] Create empty test modules `tests/unit/test_design_workflow_skill.py` and `tests/unit/test_design_reference_layout.py`, each with a module docstring citing `specs/014-reference-driven-ui/contracts/` and path constants built like `TEMPLATE_PATH` in `tests/unit/test_web_static_assets.py`: `REPO_ROOT = Path(__file__).resolve().parents[2]`, `SKILL_DIR = REPO_ROOT / ".claude/skills/frontend-design"`, `DESIGN_DIR = REPO_ROOT / "design"`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The skill file's frontmatter and section skeleton, which every story fills in.

**⚠️ CRITICAL**: Complete before Phase 3+.

- [X] T003 Write a test in `tests/unit/test_design_workflow_skill.py`: `SKILL.md` starts with YAML frontmatter (parse the text between the first two `---` lines with `yaml.safe_load`) containing `name == "frontend-design"` and a non-empty `description` that mentions `design/references`. Also test that the 8 workflow headings appear in this order: "Gather inputs", "Inspect references", "Understand the existing UI", "Design interpretation", "Implement", "Verify visually", "Refine", "Report" (assert by increasing `str.index`). Run it and confirm it FAILS (the file is currently empty).
- [X] T004 Write the skeleton of `.claude/skills/frontend-design/SKILL.md`:
  - frontmatter `name: frontend-design`, plus a `description` saying to use it when implementing or redesigning English Tutor web UI from references in `design/references/<page>/`;
  - a one-paragraph purpose statement;
  - a precedence statement: the project rules here override generic aesthetic guidance, including the `frontend-design:frontend-design` plugin skill;
  - the 8 `##` workflow headings from T003 as numbered sections, with one-line placeholders.

  Make T003 pass.

**Checkpoint**: The skill loads with a valid name and description. The stories fill in its sections.

---

## Phase 3: User Story 1 - Store references and get a design interpretation first (Priority: P1) 🎯 MVP

**Goal**: The developer drops screenshots into `design/references/<page>/`. Claude inspects them and writes a design interpretation before editing anything.

**Independent Test**: Put 2 images in `design/references/vocabulary-practice/`, ask for a redesign, and confirm the first output is an interpretation covering all sections in `data-model.md` (including "Not carried over") with no file edits (quickstart §4 step 3, first bullet).

### Tests for User Story 1 ⚠️ (write first, must fail)

- [X] T005 [P] [US1] In `tests/unit/test_design_reference_layout.py`, test that `design/references/{vocabulary-practice,sentence-practice,progress,shared}/` each exist and contain `.gitkeep`, and that `design/README.md` exists and mentions: each of the four folder names, `notes.md`, accepted image types (`png`, `jpg`), "runtime" (nothing used at runtime), and "logo" (do-not-copy). Confirm it FAILS.
- [X] T006 [P] [US1] In `tests/unit/test_design_workflow_skill.py`, test that `SKILL.md`:
  - links `reference-analysis.md` and `design-interpretation.md`, and both files exist in `SKILL_DIR`;
  - includes a do-not-copy list containing "logos", "trademarks", "illustrations", "copy" and "scrap" (no scraping);
  - in its "Gather inputs" section names `design/references/` and `shared/`.

  Also test that `reference-analysis.md` mentions each analysis dimension from FR-010: layout, hierarchy, typography, spacing, alignment, density, color, border, radius, shadow, button, input, card, navigation, feedback, responsive. Test that `design-interpretation.md` contains every section title from `specs/014-reference-driven-ui/data-model.md` "Design Interpretation", including "Not carried over" and "Conflicts". Confirm it FAILS.

### Implementation for User Story 1

- [X] T007 [P] [US1] Create `design/references/vocabulary-practice/.gitkeep`, `design/references/sentence-practice/.gitkeep`, `design/references/progress/.gitkeep` and `design/references/shared/.gitkeep`.
- [X] T008 [P] [US1] Write `design/README.md` per `contracts/reference-folder-contract.md`:
  - the purpose of each folder;
  - accepted image types `.png/.jpg/.jpeg/.webp`;
  - optional `notes.md` for intent ("like ref-1's spacing, ignore its sidebar");
  - references are inspiration only: no logos, trademarks, illustrations or copied text get into the product;
  - nothing under `design/` is used at runtime;
  - adding a page means creating `design/references/<page-key>/`;
  - the trigger sentence: "Redesign the <page> page using the frontend-design skill and the references in design/references/<page>."
- [X] T009 [P] [US1] Write `.claude/skills/frontend-design/reference-analysis.md`: a checklist with one bullet per FR-010 dimension. Each bullet says what to observe (e.g. "Typography: size ratio prompt:body, weights used, line-height, case"). It closes with "extract principles, not pixels" and the rules for unreadable or unsupported files: skip and report.
- [X] T010 [P] [US1] Write `.claude/skills/frontend-design/design-interpretation.md`: a fill-in template whose sections exactly match `data-model.md` "Design Interpretation" (References used, Visual direction, Typography hierarchy, Spacing system, Actions, Component treatment, Feedback behavior, Responsive strategy, Not carried over, Conflicts / decisions). Include one short worked example adapted to a learning page, e.g. "Large exercise prompt; one dominant primary action".
- [X] T011 [US1] Fill in these `SKILL.md` sections in `.claude/skills/frontend-design/SKILL.md`:
  - "Gather inputs": resolve the target page from the request; the reference set is `design/references/<page>/` + `shared/` + optional `notes.md`; find the template, CSS and JS that render the page.
  - "Inspect references": view every image and follow `reference-analysis.md`.
  - "Understand the existing UI": read the template, CSS custom properties/classes, JS state rendering and the existing static-asset tests before proposing anything.
  - "Design interpretation": fill in `design-interpretation.md` and show it to the developer before any edit.

  Add the do-not-copy list (logos, trademarks, proprietary illustrations, copyrighted or reference copy text, brand assets; never download or scrape sites; a website name instead of a screenshot means general knowledge only, or ask for a screenshot). Make T005 and T006 pass (T005 also needs T007 and T008).

**Checkpoint**: References have a home, and Claude can produce a reviewable interpretation. MVP done.

---

## Phase 4: User Story 2 - Implement without changing learning behavior (Priority: P1)

**Goal**: Implementation stays within the existing stack and components, keeps behavior and accessibility, and never makes the app depend on `design/`.

**Independent Test**: The full `pytest` suite is green before and after a redesign. The app serves `/` with `design/` absent (quickstart §2).

### Tests for User Story 2 ⚠️

- [X] T012 [P] [US2] In `tests/unit/test_design_reference_layout.py`, add these runtime-boundary tests:
  - (a) No file under `src/` (glob `**/*` for `.py`, `.html`, `.css`, `.js`) contains the substring `design/`.
  - (b) Using `monkeypatch.chdir(tmp_path)` and a tmp vocab dir holding one block in the existing format (`english`, `alternates`, `chinese`, `group`), `create_app(vocab_dir=..., progress_file=tmp_path/"progress.md")` from `src.web.app` gives a test client whose `GET /` and `GET /static/style.css` both return 200.

  (a) passes today. It is a guard, so confirm it by temporarily adding the string to a scratch copy, not to `src/`. (b) also passes today and guards SC-004.
- [X] T013 [P] [US2] In `tests/unit/test_design_workflow_skill.py`, test that `SKILL.md` contains:
  - the learning UI rules from FR-006 (substrings: "visual focus", "dashboard", "one", "primary action", "correct", "incorrect", "loading", "sentence practice", "progress", "mobile");
  - the accessibility floor ("semantic", "keyboard", "focus", "contrast", "label", "44");
  - "stop and ask" plus "learning behavior";
  - "pytest" (run the suite before and after);
  - that it never tells you to modify `pyproject.toml`: no line contains both "add" and "pyproject".

  Confirm it FAILS.

### Implementation for User Story 2

- [X] T014 [US2] Fill in the "Implement" section of `.claude/skills/frontend-design/SKILL.md`:
  - run `pytest -q` before editing and record the baseline;
  - use the existing stack (Jinja template, plain CSS with existing custom properties in `:root` and its dark-mode block, vanilla JS);
  - extend existing classes and tokens before adding new ones;
  - no new dependencies, build step or framework;
  - JS changes are presentation-only;
  - keep the `[hidden]` guarantee;
  - update the static-asset tests if class names they assert change, and say so;
  - run `pytest -q` after editing; it must match the baseline.

  Add a "Learning UI rules" checklist (FR-006), an "Accessibility floor" checklist (semantic HTML, keyboard operation, visible focus, WCAG AA contrast, labelled inputs, ≥44px touch targets on narrow layouts, references never override these), and a "Stop and ask" list: the change would alter learning behavior; no references found; references conflict materially. Make T013 pass.

**Checkpoint**: US1 + US2 give a complete interpret → implement workflow with behavior and runtime guarantees.

---

## Phase 5: User Story 3 - Visually verify and refine on desktop and mobile (Priority: P2)

**Goal**: After implementing, Claude screenshots the page at 1280 and 390 in the relevant states, compares, fixes and repeats (at most 3 passes), or plainly reports that verification was skipped.

**Independent Test**: With browser tooling, a redesign produces `design/verification/<page>/pass-0/` and `pass-1/` captures at both widths, plus a findings list (quickstart §3–4).

### Tests for User Story 3 ⚠️

- [X] T015 [P] [US3] In `tests/unit/test_design_reference_layout.py`, test that `.gitignore` has a line `/design/verification/`. Test that `design/fixtures/vocabulary/sample.md` loads through `src.services.vocabulary_loader.load_vocabulary(DESIGN_DIR / "fixtures/vocabulary")` with an empty warnings list, 3–5 items, all with `group == "design-fixture"`, and at least one item with non-empty `alternates`. Confirm it FAILS.
- [X] T016 [P] [US3] In `tests/unit/test_design_workflow_skill.py`, test that:
  - `SKILL.md` links `visual-verification.md` and the file exists;
  - `visual-verification.md` contains `design/fixtures/vocabulary`, `--port 8421`, `127.0.0.1`, `1280`, `390`, `npx`, `playwright`, "skipped" and `design/verification/`, and each comparison category: spacing, sizing, alignment, typography, density, hierarchy, consistency;
  - `SKILL.md` mentions "3" passes in its "Refine" section and the word "skipped" in "Verify visually";
  - the "Report" section lists: references, interpretation, files changed, screenshots, deviations.

  Confirm it FAILS.

### Implementation for User Story 3

- [X] T017 [P] [US3] Create `design/fixtures/vocabulary/sample.md` with 4 blocks in the existing format (see `vocabulary/T_words.md`), all `group: design-fixture`, plain common words: one with `alternates: [story]`-style alternates and one with a multi-meaning `chinese` field. Avoid YAML 1.1 boolean spellings like `yes`/`no`/`on`/`off` as words (see commit c478040).
- [X] T018 [P] [US3] Append `/design/verification/` to `.gitignore` under a `# Design workflow screenshots (spec 014)` comment.
- [X] T019 [P] [US3] Write `.claude/skills/frontend-design/visual-verification.md` from `specs/014-reference-driven-ui/contracts/verification-recipe.md`:
  - §1 start an isolated instance on 127.0.0.1:8421 with the fixture vocabulary and `design/verification/progress.md`, in the background, and wait on `/api/state`;
  - §2 the state-driving table using `/api/select` body `{"collection": "design-fixture", "order": ..., "mode": ...}` plus `/api/answer`, `/api/sentence`, `/api/skip` and `/api/continue`, and the note to check field names in `src/web/app.py`;
  - §3 the tooling ladder (load `anthropic-skills:built-in-browser` or `anthropic-skills:chrome-browser` before using those tools; else `npx -y playwright screenshot --viewport-size=W,H --full-page`; else report "Visual verification skipped: <reason>" with manual steps) and the screenshot path `design/verification/<page>/pass-<N>/<state>-<width>.png`;
  - §4 the comparison checklist with fix / intentional (reason) / matches, compared against the interpretation, not pixels;
  - §5 the loop and stop rules;
  - a note that transient states (loading/review) must disappear after completion, and that this is checked by reading `app.js`/CSS when only the CLI tool is available.
- [X] T020 [US3] Fill in the "Verify visually", "Refine" and "Report" sections of `.claude/skills/frontend-design/SKILL.md`:
  - verify at both widths and in all states the change touches, following `visual-verification.md`;
  - never claim verification that didn't happen;
  - refine: fix every *fix* finding, re-capture, at most 3 refine passes, no pixel-matching at the cost of content, usability, accessibility or responsiveness, and state intentional deviations;
  - report: references used, interpretation, files changed, test results before and after, screenshot paths per pass, fixes, intentional deviations, remaining differences;
  - stop the verification server.

  Make T015 and T016 pass (T015 also needs T017 and T018).

**Checkpoint**: The full workflow, including the screenshot → compare → refine loop, is documented and testable.

---

## Phase 6: User Story 4 - Reuse for future pages (Priority: P3)

**Goal**: Any page works by adding a reference folder. The skill never needs editing.

**Independent Test**: `SKILL.md` contains no page-specific selectors. Running the workflow for a second folder leaves `git diff .claude/skills/frontend-design/` empty (quickstart §4 step 5).

### Tests for User Story 4 ⚠️

- [X] T021 [US4] In `tests/unit/test_design_workflow_skill.py`, test that none of `SKILL.md`, `reference-analysis.md`, `design-interpretation.md` or `visual-verification.md` contains any element id actually present in `src/web/templates/index.html`. Extract them with `re.findall(r'id="([^"]+)"', html)` and check for `#<id>`. This keeps the guard tied to the real page rather than a hard-coded list. Confirm it passes against the content from T009–T020. If it fails, remove the page-specific reference from the skill file.

### Implementation for User Story 4

- [X] T022 [US4] Review `.claude/skills/frontend-design/SKILL.md` "Gather inputs" and make sure it handles any `<page-key>`: an unknown or new folder name is fine; an empty folder (only `.gitkeep`) means "no references → stop and ask"; files in `shared/` apply to every page. Make sure page names appear only as examples. Re-run T021.

**Checkpoint**: All four stories are complete. The skill is page-independent.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T023 [P] Add a short "Design workflow" subsection under `## Development` in `README.md`: where references go (`design/references/<page>/`), the trigger sentence, and that `design/` is dev-only.
- [X] T024 Run `ruff check tests/unit/test_design_workflow_skill.py tests/unit/test_design_reference_layout.py` and fix any issues.
- [X] T025 Run the full `pytest -q` and confirm: all new tests pass, and the pass count = T001 baseline + new tests, with no previously passing test now failing.
- [X] T026 Run quickstart §2 (runtime independence with `design/` moved aside, port 8422) and §3 (isolated instance on 8421, `/api/select` with `"collection": "design-fixture"`, `/api/state` shows recall with a fixture word; `git status` shows `progress.md` and `vocabulary/` untouched). Record the results in Notes below.
- [X] T027 If browser tooling or `npx playwright` is available, take one smoke capture of the choose state at 1280 and 390 into `design/verification/smoke/` to show the recipe works end to end. Otherwise record "skipped: <reason>" in Notes. This feature does not redesign any page.

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup (T001–T002) → Foundational (T003–T004) → US1 → US2 → US3 → US4 → Polish.
- US1–US3 each fill different sections of the same `SKILL.md`, so their final SKILL.md
  tasks (T011, T014, T020) run one after another. Their sibling files, `design/` assets
  and tests can be done in parallel.

### User Story Dependencies

- **US1 (P1)**: needs Foundational only.
- **US2 (P1)**: needs Foundational. Logically independent of US1, but T014 edits the same file as T011.
- **US3 (P2)**: needs Foundational. T020 comes after T014 (same file).
- **US4 (P3)**: needs US1–US3 content to exist (it audits all skill files).

### Within Each User Story

- Test tasks first, confirmed failing (except T012's guards, which pass today) → content → test passes.

### Parallel Opportunities

- T002 can run alongside T001.
- US1: T005 ∥ T006; then T007 ∥ T008 ∥ T009 ∥ T010; then T011.
- US2: T012 ∥ T013, and both can run in parallel with US1's file tasks.
- US3: T015 ∥ T016; then T017 ∥ T018 ∥ T019; then T020.
- Polish: T023 alongside T024.

---

## Parallel Example: User Story 1

```text
# Tests together (both must fail):
T005 tests/unit/test_design_reference_layout.py — folder + README contract
T006 tests/unit/test_design_workflow_skill.py — analysis/interpretation/do-not-copy

# Content together (four different files):
T007 design/references/*/.gitkeep
T008 design/README.md
T009 .claude/skills/frontend-design/reference-analysis.md
T010 .claude/skills/frontend-design/design-interpretation.md

# Then sequentially:
T011 .claude/skills/frontend-design/SKILL.md sections 1–4
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. T001–T004 → skill skeleton.
2. T005–T011 → references folder + interpretation-first workflow.
3. **Stop and validate**: ask Claude for an interpretation from a sample reference.

### Incremental Delivery

1. + US2 → implement safely (behavior, accessibility, runtime boundary).
2. + US3 → screenshot → compare → refine loop.
3. + US4 → page-independence guard.
4. Polish → README, lint, full suite, quickstart checks.

---

## Notes

- `src/` must not change in this feature. If any task seems to need it, stop and ask.
- Commit after each phase checkpoint.
- Baseline (T001): 239 passed with `.venv/bin/python -m pytest -q`, including the uncommitted `llm_client.py` / Ollama contract test changes. No pre-existing failures. After this feature: 265 passed (239 + 26 new).
- Quickstart results (T026): §2: a copy of `src/` run from a scratch directory with no `design/` served `GET /` and `GET /static/style.css` with 200. §3: the isolated instance on 127.0.0.1:8421 listed `design-fixture` (4 words). `/api/select` with `"collection": "design-fixture"` and `"mode": "recall-only"` gave a recall state for 河；江, and a wrong answer returned `correct: false`. The real `progress.md` mtime was unchanged (2026-09-28). `design/verification/` is git-ignored.
- T027 smoke screenshots: done. Installed Chromium with `npx -y playwright install chromium`, ran the isolated instance on 127.0.0.1:8421, and captured `design/verification/smoke/choose-1280.png` and `choose-390.png` with `npx -y playwright screenshot --full-page`. Both show the choose screen with the `design-fixture` (4) collection and no horizontal overflow at 390px. Observation for a future redesign, not fixed here: the Order/Mode radio buttons are well under the skill's 44px touch-target floor at 390px.
