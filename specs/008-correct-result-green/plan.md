# Implementation Plan: Show a Correct Recall Result in Green

**Branch**: `008-correct-result-green` | **Date**: 2026-09-20 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/008-correct-result-green/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

The recall-step result banner (`#word-feedback`, spec `004`/`006`) currently
renders both outcomes in the same red ink, distinguished only by the ✓/✗
symbol and wording — a deliberate choice at the time, to avoid a red/green
pairing that's hard to tell apart for the most common form of color
blindness. This feature adds a distinct green for the correct case only,
while keeping the ✓/✗ symbol and wording distinction exactly as-is (spec.md
FR-002), so the accessibility guarantee holds either color-sighted or not.
This is a CSS-only change: `app.js` already toggles a `.feedback-correct`/
`.feedback-incorrect` class pair per outcome (added in spec `004`) — no
markup or script logic needs to change, only what `.feedback-correct`
looks like.

## Technical Context

**Language/Version**: CSS (existing `src/web/static/style.css`); no Python or JS logic changes

**Primary Dependencies**: None new — reuses the existing custom-property token system (`--red`, `--red-tint`, `--ink-rgb`, etc.) already established in `style.css`

**Storage**: N/A

**Testing**: Extend the existing static-content assertion convention (`tests/unit/test_web_static_assets.py`) — this project has no JS/browser test runner (established since `003`); a manual real-browser pass (light and dark) is still required, per `research.md` §3

**Target Platform**: Existing web UI, unchanged

**Project Type**: Single project — this feature touches exactly one file, `src/web/static/style.css`

**Performance Goals**: N/A

**Constraints**:
- MUST NOT change `src/web/static/app.js` or `src/web/templates/index.html` — the `.feedback-correct`/`.feedback-incorrect` class-toggling and markup already exist and are correct; only the CSS changes
- MUST keep `.feedback-correct::before`/`.feedback-incorrect::before`'s ✓/✗ content exactly as-is (spec.md FR-002)
- MUST NOT change `.feedback-incorrect`'s appearance at all (spec.md FR-003)
- New green MUST be legible (sufficient contrast against the card background) in both the existing light and dark palettes (`style.css`'s `@media (prefers-color-scheme: dark)` block)

**Scale/Scope**: One new pair of CSS custom properties (a green + a green-tint, mirroring the existing `--red`/`--red-tint`) and one new rule block scoping them to `.feedback-correct`; no new files, dependencies, entities, or endpoints

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| I. Test-First Development (NON-NEGOTIABLE) | Plan requires a static-content regression test (asserting `.feedback-correct` uses a distinct green token, not `--red`, while `.feedback-incorrect` is unchanged) written before the CSS change, following this project's established "no JS runner, static assertions + manual browser pass" convention (`005`/`006`/`007`) | PASS |
| II. Pedagogical Accuracy & Safety | No language generation/grading/scoring logic touched — purely a display color for an already-computed correct/incorrect outcome | PASS (N/A) |
| III. Learner Data Privacy | No data collected, stored, or changed | PASS (N/A) |

**Accessibility note** (not a constitution gate, but directly relevant given this project's established practice of documenting such tradeoffs explicitly — see `006`'s FR-016 note and `007`'s "no skip/back" note): spec.md FR-002 requires the ✓/✗ symbol and wording distinction to remain, specifically so the result stays distinguishable without relying on color. This plan keeps `.feedback-correct::before`/`.feedback-incorrect::before` untouched, satisfying that requirement structurally rather than by convention alone.

**Post-design re-check**: Phase 1 artifacts (data-model.md, quickstart.md) introduce no new entities, endpoints, or logic beyond a CSS token pair — all three gates still PASS unchanged. No `contracts/` directory is produced — this feature adds no new interface (see Project Structure).

## Project Structure

### Documentation (this feature)

```text
specs/008-correct-result-green/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command) — no entities; kept for consistency
└── quickstart.md        # Phase 1 output (/speckit-plan command)
```

No `contracts/` directory: this feature adds no new API endpoint, CLI flag,
or other external interface — the existing `GET /api/state`/word-feedback
contract (`004`'s delta) is unchanged; only its rendered color changes.

### Source Code (repository root)

```text
src/
└── web/
    └── static/
        └── style.css    # + --green/--green-tint tokens (light + dark), + .feedback-correct color override

tests/
└── unit/
    └── test_web_static_assets.py    # + assertion that .feedback-correct uses the new green token, not --red
```

**Structure Decision**: Single project (existing layout, established `001`–`007`). This is the smallest feature in the project so far by file count — one source file changed, one test file extended.

## Complexity Tracking

*No constitution violations requiring justification. Table omitted.*
