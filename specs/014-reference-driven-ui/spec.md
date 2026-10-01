# Feature Specification: Reference-Driven UI Design Workflow

**Feature Branch**: `014-reference-driven-ui`

**Created**: 2026-10-01

**Status**: Draft

**Input**: User description: "Create a reusable workflow that allows Claude Code to implement or redesign frontend pages based on visual references such as screenshots or well-known websites, while adapting the design principles to the English Tutor product rather than blindly copying the reference. The workflow should combine reference analysis, a reusable frontend design skill, implementation, browser-based visual verification, screenshot comparison, and iterative refinement."

## User Scenarios & Testing *(mandatory)*

The "user" of this feature is a developer working on English Tutor with an AI coding assistant. The "end user" whose experience must be protected is the learner using the practice pages.

### User Story 1 - Store references and get a design interpretation before any code changes (Priority: P1)

A developer drops one or more reference screenshots into a predictable folder for the page they want to improve (e.g. `design/references/vocabulary-practice/`) and asks the assistant to redesign that page. Before touching any page code, the assistant inspects every reference image and the current page, then produces a short written design interpretation: visual direction, typography hierarchy, spacing system, primary/secondary actions, component treatment, feedback behavior, and responsive strategy. That interpretation is explicitly adapted to English Tutor's learning rules rather than describing the reference site.

**Why this priority**: The interpretation is the step that turns "make it look like this" into concrete, reviewable design decisions. Without it, every later step is guesswork and the developer falls back to manual prompts like "move this button". It is also useful on its own: a developer can review or reject the direction before any implementation effort is spent.

**Independent Test**: Place two screenshots in a page's reference folder, ask for a redesign, and confirm the assistant's first output is a design interpretation covering all seven topics, mentions what it is deliberately *not* carrying over from the reference (logos, brand colors used as identity, copy text), and that no page files have been modified yet.

**Acceptance Scenarios**:

1. **Given** the folder `design/references/vocabulary-practice/` contains `reference-1.png` and `reference-2.png`, **When** the developer asks "Redesign the vocabulary practice page using the frontend-design skill and the references in design/references/vocabulary-practice", **Then** the assistant reports having inspected both images and the current page before proposing changes.
2. **Given** the references have been inspected, **When** the assistant presents its design interpretation, **Then** it covers visual direction, typography hierarchy, spacing system, primary/secondary actions, component treatment, feedback behavior, and responsive strategy.
3. **Given** a reference contains a company logo, brand illustration, or marketing copy, **When** the interpretation is written, **Then** those assets are explicitly excluded and only the underlying principles (e.g. "generous whitespace around a single focal prompt") are carried forward.
4. **Given** a reference shows a dashboard-style layout with many cards, **When** the interpretation is written, **Then** it adapts the style to keep the current exercise as the single visual focus rather than reproducing the dashboard structure.

---

### User Story 2 - Implement the redesign without changing learning behavior (Priority: P1)

Following the design interpretation, the assistant changes the page's presentation using the project's existing frontend stack, existing components and existing styles wherever practical. The learning workflow — word order, practice mode, recall checks, confirm-before-continue on wrong answers, sentence review, progress tracking, voice input — behaves exactly as before.

**Why this priority**: A redesign that breaks the learning flow is a regression, not an improvement. Preserving behavior is a hard constraint on every use of the workflow.

**Independent Test**: Run the project's full existing automated test suite before and after a redesign; all previously passing tests still pass. Manually walk through one full practice session (correct answer, wrong answer with confirmation, sentence practice, progress update) and confirm identical behavior.

**Acceptance Scenarios**:

1. **Given** a redesign has been implemented, **When** the existing automated tests are run, **Then** every test that passed before the redesign still passes.
2. **Given** a learner answers a word correctly, **When** the redesigned page shows the result, **Then** it advances exactly as it did before and the correct state is visually distinct from the incorrect state.
3. **Given** a learner answers incorrectly in recall-only mode, **When** the result is shown, **Then** the confirm-before-continue step still appears and still requires the learner's action.
4. **Given** the redesign needs a visual element the page already has a component for, **When** implementing, **Then** the existing component is adapted or extended rather than a duplicate created.
5. **Given** a redesign is complete, **When** the application is run with the `design/` folder absent, **Then** the application starts and every page renders normally.

---

### User Story 3 - Visually verify and refine on desktop and mobile (Priority: P2)

After implementing, the assistant starts the application, opens the changed page in a browser at a desktop width and a narrow/mobile width, captures screenshots, and compares them against the references and the design interpretation. It lists meaningful differences (spacing, sizing, alignment, typography, density, hierarchy, inconsistent component styling), fixes them, and captures new screenshots. It repeats until the result is reasonably aligned or remaining differences are intentional.

**Why this priority**: This closes the loop that otherwise requires the developer to eyeball the page and send correction prompts. It depends on browser tooling being available, so the workflow must still deliver Stories 1–2 without it.

**Independent Test**: With browser tooling available, perform a redesign and confirm the assistant's report contains at least one before/after pair of screenshots per viewport, a list of differences found in the first pass, and the changes made in response.

**Acceptance Scenarios**:

1. **Given** browser tooling is available and the redesign is implemented, **When** verification runs, **Then** the assistant captures screenshots of the changed page at both a desktop and a narrow/mobile width.
2. **Given** the first screenshots show a meaningful difference (e.g. prompt text much smaller than the reference's focal text), **When** the assistant compares, **Then** it names the difference, makes a fix, and captures a new screenshot to confirm.
3. **Given** a difference exists only because matching the reference would harm usability, accessibility, readable content, or responsive behavior, **When** comparing, **Then** the assistant keeps the difference and states why instead of forcing a match.
4. **Given** the page has transient states (loading, reviewing, correct, incorrect, sentence practice), **When** verifying, **Then** the assistant checks the relevant states, including that loading/review indicators are gone once the action completes and sentence practice stays hidden until appropriate.
5. **Given** browser tooling is not available, **When** the workflow reaches verification, **Then** the assistant states that visual verification was skipped, and tells the developer how to check it themselves.

---

### User Story 4 - Reuse the same workflow for future pages (Priority: P3)

A later request such as "Redesign the progress page using the frontend-design skill and the references in design/references/progress" works the same way, without editing the skill. Page-specific requirements come from the request, the reference folder, and the page itself, not from the skill.

**Why this priority**: Reusability is what makes this a workflow rather than a one-off redesign. It matters once the first page is done.

**Independent Test**: Inspect the skill and confirm it contains no instructions specific to one page; run the workflow for a second page folder and confirm the skill file is unchanged.

**Acceptance Scenarios**:

1. **Given** the frontend-design skill exists, **When** a developer reads it, **Then** it contains general methodology and English Tutor-wide learning UI rules, with no instructions tied to a single page.
2. **Given** references exist in `design/references/sentence-practice/`, **When** the developer requests a redesign of the sentence practice area, **Then** the assistant follows the same workflow with no change to the skill.
3. **Given** a reference applies across pages (e.g. a button style), **When** it is placed in `design/references/shared/`, **Then** the assistant considers it alongside page-specific references for any page.

---

### Edge Cases

- **Empty or missing reference folder**: The assistant says no references were found and asks whether to proceed using only the skill's general rules or wait for references. It does not invent a reference.
- **Conflicting references**: When two references disagree (e.g. dense vs. airy), the interpretation names the conflict and picks one direction with a stated reason, or asks the developer if the choice materially changes the page.
- **Reference of a completely different product type** (e.g. a checkout page): Only transferable principles are taken; the learning UI rules win over the reference.
- **Reference given as a website name instead of a screenshot**: The assistant works from its general knowledge of that site's design language or asks for a screenshot. It never downloads or scrapes the site.
- **Unsupported or unreadable file** in a reference folder: It is skipped and reported, and the remaining references are still used.
- **App fails to start or the page fails to load during verification**: The assistant reports the failure and does not claim visual verification succeeded.
- **The redesign would require changing learning behavior** (e.g. a reference shows answers revealed before submission): The assistant does not make that change and asks the developer to confirm explicitly.
- **Verification never converges**: After a bounded number of refinement passes (see FR-019), the assistant stops, reports the remaining differences, and hands the decision to the developer.
- **Reference colors give poor contrast for text**: Contrast requirements win; the color is adjusted and the deviation noted.

## Requirements *(mandatory)*

### Functional Requirements

**Reference storage**

- **FR-001**: The project MUST provide a predictable reference location at `design/references/` with sub-folders `vocabulary-practice/`, `sentence-practice/`, `progress/`, and `shared/`, plus a short note explaining what belongs there and what must not be stored there.
- **FR-002**: Developers MUST be able to add new page folders under `design/references/` without changing the skill.
- **FR-003**: Nothing under `design/` MUST be loaded, served, bundled, or required by the application at runtime.

**Frontend design skill**

- **FR-004**: A reusable project skill MUST exist at `.claude/skills/frontend-design/SKILL.md` (the file currently exists but is empty and will be filled in).
- **FR-005**: The skill MUST describe a general methodology, in this order: inspect references → understand the existing page and frontend architecture → extract design principles → write the design interpretation → implement with the existing stack → visually verify → refine.
- **FR-006**: The skill MUST contain the English Tutor-wide learning UI rules: the current exercise stays the visual focus; no unnecessary dashboard-style UI, excessive cards, or distracting decoration; exactly one obvious primary action per exercise state; correct and incorrect answers visually distinct; loading/review states not visible after they finish; sentence practice hidden until appropriate; progress visible but not dominant; works on desktop and mobile.
- **FR-007**: The skill MUST NOT contain instructions specific to a single page. Page-specific requirements come from the developer's request, the reference folder, and the page itself.
- **FR-008**: The skill MUST instruct the assistant to avoid new dependencies unless clearly necessary and justified, and to avoid generic "AI-generated dashboard" aesthetics.

**Reference analysis and design interpretation**

- **FR-009**: Before changing any page code, the assistant MUST inspect every readable reference in the target page folder and in `shared/`.
- **FR-010**: The analysis MUST cover: overall layout, information hierarchy, typography (sizes and weights), spacing, alignment, content density, colors, borders, border radius, shadows, buttons, inputs, cards, navigation, feedback states, and responsive behavior.
- **FR-011**: The assistant MUST produce a short design interpretation before implementation covering visual direction, typography hierarchy, spacing system, primary/secondary actions, component treatment, feedback behavior, and responsive strategy.
- **FR-012**: The interpretation and implementation MUST NOT copy logos, trademarks, proprietary illustrations, copyrighted text, or brand-specific assets from references. Only principles are carried over.

**Implementation constraints**

- **FR-013**: The redesign MUST NOT change learning behavior (answer checking, word ordering, practice modes, confirmation steps, sentence review, progress tracking, voice input) unless the developer explicitly requests it.
- **FR-014**: The redesign MUST reuse and extend existing components and styles where practical and MUST NOT rewrite the frontend architecture or replace the frontend framework to match a reference.
- **FR-015**: The redesign MUST preserve accessibility: semantic structure, keyboard navigation, visible focus states, readable contrast, labelled form inputs, and comfortably sized interactive targets.

**Visual verification**

- **FR-016**: When browser tooling is available, the assistant MUST start the application, open the changed page, and capture screenshots at a desktop width and a narrow/mobile width.
- **FR-017**: The assistant MUST compare the screenshots with the references and design interpretation, list meaningful differences (spacing, sizing, alignment, typography, density, hierarchy, component consistency), fix them, and capture new screenshots. At least one full screenshot → compare → refine cycle MUST be performed.
- **FR-018**: Verification MUST check the page states relevant to the change, including correct, incorrect, loading/review completion, and sentence-practice visibility where applicable.
- **FR-019**: The refine loop MUST stop when no meaningful differences remain or after at most 3 refinement passes, after which remaining differences are reported to the developer.
- **FR-020**: The assistant MUST NOT pursue pixel-level matching where it would conflict with real content, usability, accessibility, or responsive behavior, and MUST state any intentional deviations.
- **FR-021**: When browser tooling is unavailable or the app cannot be run, the assistant MUST say so plainly and MUST NOT claim visual verification occurred.

**Reporting**

- **FR-022**: At the end of a redesign the assistant MUST report: references used, the design interpretation, files changed, verification screenshots taken (or why none were), differences fixed, and intentional deviations.

### Key Entities

- **Reference Set**: A folder of reference images for one page (or `shared/` for cross-page references). Design-time input only.
- **Design Interpretation**: A short written translation of the references into English Tutor design decisions across seven topics. Produced before implementation and included in the final report.
- **Frontend Design Skill**: The reusable methodology and English Tutor-wide learning UI rules. Page-independent.
- **Verification Screenshot**: A capture of the implemented page at a given viewport and state, used for comparison and kept out of the application's runtime.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer can request a full page redesign with a single sentence naming the skill and a reference folder, and gets a complete result (interpretation, implementation, verification report) without further layout instructions such as "move this button" or "increase spacing" in at least 4 out of 5 redesign requests.
- **SC-002**: 100% of tests that passed before a redesign still pass afterwards.
- **SC-003**: Every redesign performed with browser tooling available includes screenshots at 2 viewport widths (desktop and narrow/mobile) and at least 1 refine cycle.
- **SC-004**: The application starts and all pages render with the `design/` folder deleted.
- **SC-005**: Zero logos, trademarks, proprietary illustrations, or reference-site copy text appear in the implemented pages.
- **SC-006**: A second page can be redesigned with the workflow with zero edits to the skill file.
- **SC-007**: On the redesigned page, a first-time viewer can identify the current exercise and its single primary action within 5 seconds at both viewport widths.
- **SC-008**: All text on redesigned pages meets standard readable-contrast levels (WCAG AA), and every interactive element is reachable and operable by keyboard with a visible focus indicator.

## Assumptions

- The workflow is used by a developer working with an AI coding assistant that can read images in the repository; it is not an end-user feature.
- Browser tooling for screenshots may or may not be available in a given session; the workflow degrades to "interpret + implement + report that verification was skipped" when it is not.
- "Desktop" means roughly 1280px wide and "narrow/mobile" means roughly 375–390px wide.
- The existing empty `.claude/skills/frontend-design/SKILL.md` is the intended home for the skill and will be filled in rather than replaced with a new location.
- Reference images are typically PNG or JPEG screenshots supplied by the developer, and whether the developer may use them as design inspiration is their responsibility; the workflow only guarantees no assets are copied into the product.
- Whether reference images and verification screenshots are committed to version control is the developer's choice. Verification screenshots are stored outside the application's served files.
- The first concrete use is the vocabulary practice page, but this feature delivers the workflow and skill. A specific page redesign is a separate request run through the workflow.
- No learner data is collected, stored, or transmitted by this feature (Constitution Principle III not engaged). Constitution Principle I is satisfied by keeping the existing behavior test suite green and adding tests for anything new that affects the runtime (e.g. confirming the app does not depend on `design/`).
