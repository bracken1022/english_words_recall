# Implementation Plan: Fix Web UI State Visibility

**Branch**: `005-fix-ui-visibility-bug` | **Date**: 2026-09-19 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/005-fix-ui-visibility-bug/spec.md`

## Summary

A single-root-cause CSS fix, confirmed by reading the actual shipped file
(`src/web/static/style.css`): `section { display: flex; ... }` and
`.spinner { display: flex; ... }` both set `display` on elements the app
also toggles via the HTML `hidden` attribute. In every browser, an author
stylesheet rule that sets `display` on an element overrides `hidden`'s
effect — so every `<section>` (`empty-view`, `complete-view`,
`recall-view`, `sentence-view`, `feedback-view`) and the spinner have been
rendered regardless of what `app.js`'s `showOnly(step)` / `spinnerEl.hidden
= ...` logic believed it was doing. This explains all four reported
symptoms as one defect. The fix is one CSS rule restoring `hidden`'s
guarantee project-wide, plus a regression-guard test — no HTML or JS
structural change, and no change to `003`/`004`'s already-correct state
logic, word-feedback rendering, duplicate-submission guard, or responsive
layout.

## Technical Context

**Language/Version**: Python 3.11+ / vanilla JS+CSS (same as `003`/`004`,
unchanged)

**Primary Dependencies**: None new.

**Storage**: Unchanged — this is a rendering-only fix; no data, entity, or
persistence change.

**Testing**: `pytest`, extending the static-content-assertion pattern
`004` established (`tests/unit/test_web_static_assets.py`) with a
regression guard: assert `style.css` contains a rule that gives `[hidden]`
elements `display: none` with priority sufficient to override the existing
`section`/`.spinner` rules (i.e., uses `!important`, the standard,
documented fix for this exact browser behavior — see research.md).
Confirming actual on-screen rendering remains a manual `quickstart.md`
check, consistent with `003`/`004`'s established "no browser automation
tooling" decision — this bug is proof of why that manual step matters, not
a reason to abandon the convention.

**Target Platform**: Unchanged — same running web server.

**Project Type**: Bug fix within the existing `003-web-ui` /
`004-web-ui-ux-polish` presentation layer — no new package.

**Performance Goals**: Unaffected — one additional CSS rule has no
measurable runtime cost.

**Constraints**: MUST NOT regress spec FR-008 / this project's
already-established behaviors (word-feedback text/color, the
duplicate-submission guard, input/button grouping, responsive layout,
grading, the review pipeline, progress-log format). The fix MUST be the
smallest change that restores `hidden`'s guarantee — not a rework of how
visibility is implemented, given how much of `003`/`004`'s already-tested
logic (correctly) assumes `hidden` works and only the rendering was wrong.

**Scale/Scope**: Unchanged.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| I. Test-First Development | A regression-guard test for the CSS override is written before the fix; see Project Structure and `tasks.md` (next command). | PASS |
| II. Pedagogical Accuracy & Safety | No change to grading, review, or any language-judging logic — purely a rendering fix. Nothing new for this principle to gate. | PASS |
| III. Learner Data Privacy | No new data, no new exposure. | PASS |

No violations to justify; **Complexity Tracking** is not needed for this
feature.

**Post-Phase 1 re-check**: `data-model.md` confirms no entity/state change;
`contracts/` documents the visibility guarantee as a correction to what
`003`/`004`'s contracts already assumed true, not a new contract surface.
All three gates still PASS after design.

## Project Structure

### Documentation (this feature)

```text
specs/005-fix-ui-visibility-bug/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/web/static/
└── style.css   # CHANGED: one rule added — `[hidden] { display: none !important; }`
                 # (placement/rationale in research.md); no other rule is
                 # removed or altered, so section/.spinner's own display:flex
                 # still applies whenever they are NOT hidden

tests/unit/
└── test_web_static_assets.py   # EXTENDED: regression-guard test asserting
                                  # the `[hidden]` override rule exists in
                                  # style.css
```

**Structure Decision**: One file changed, one test extended. No HTML or JS
change — `app.js`'s `showOnly()`/`.hidden` logic and `index.html`'s
structure (both already correct at the DOM level per `003`/`004`) are
untouched; only the CSS rule that was silently defeating them is fixed.

## Complexity Tracking

*No Constitution Check violations — this section is intentionally empty.*
