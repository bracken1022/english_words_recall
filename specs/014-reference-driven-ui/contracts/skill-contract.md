# Contract: `.claude/skills/frontend-design/SKILL.md`

Enforced by `tests/unit/test_design_workflow_skill.py`.

## MUST contain

1. YAML frontmatter with `name: frontend-design` and a `description` that says when to use
   it: redesigning or implementing English Tutor UI from references in `design/references/`.
2. A precedence statement: project rules in this skill override generic aesthetic guidance,
   including the `frontend-design:frontend-design` plugin skill.
3. The workflow steps as headings, in this order:
   1. Gather inputs (target page, reference set + `shared/`, the files that render the page)
   2. Inspect references → `reference-analysis.md`
   3. Understand the existing UI (template, CSS tokens/classes, JS state rendering, existing tests)
   4. Write the design interpretation → `design-interpretation.md`. Show it before editing.
   5. Implement (existing stack, extend existing classes/tokens, no new dependencies, no
      architecture rewrite, behavior unchanged; run the test suite before and after)
   6. Verify visually → `visual-verification.md`
   7. Refine (at most 3 passes)
   8. Report
4. The English Tutor learning UI rules (FR-006), stated as a checklist.
5. The accessibility floor: semantic HTML, keyboard operation, visible focus, WCAG AA
   contrast, labelled inputs, ≥44px touch targets on narrow layouts.
6. The do-not-copy list: logos, trademarks, proprietary illustrations, copyrighted/reference
   copy text, brand-specific assets. No downloading or scraping sites.
7. A "stop and ask" list: the change would alter learning behavior; there are no
   references; references conflict in a way that changes the page materially.
8. The no-tooling statement: say verification was skipped, never imply it happened.
9. Links to `reference-analysis.md`, `design-interpretation.md` and `visual-verification.md`.
   All three files exist.

## MUST NOT contain

- Page-specific DOM selectors or element ids (e.g. `#recall-view`, `#answer-input`,
  `#sentence-view`, `#continue-button`). Page details are discovered at run time.
- Instructions to add dependencies to `pyproject.toml` or a JS build step.
- Pixel-matching as a goal.
