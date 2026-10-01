---
name: frontend-design
description: English Tutor's reference-driven UI workflow. Use when implementing or redesigning any English Tutor web page, especially when the developer points at reference screenshots in design/references/<page>/. Runs inspect references → design interpretation → implement in the existing stack → screenshot at desktop and mobile → compare → refine.
---

# Frontend design: reference-driven workflow

Turn reference screenshots into an English Tutor page that follows their
*design principles* without copying them, keeps the learning flow exactly as
it is, and is checked visually rather than assumed.

**Precedence**: the rules in this skill override generic aesthetic guidance,
including the `frontend-design:frontend-design` plugin skill. You may use that
skill for taste, but where it suggests bold decoration, new fonts or
dependencies, or layout drama, the learning UI rules below win.

This skill is page-independent. Everything specific to a page comes from the
developer's request, its reference folder and the code that renders it.

## Hard rules

### Learning UI rules

- [ ] The current exercise is the visual focus. Nothing competes with it.
- [ ] No dashboard-style UI: no stat grids, sidebars or widget rows.
- [ ] No excessive cards. Box something only when the box carries meaning.
- [ ] No decoration that distracts from learning (illustrations, gradients,
      ornamental motion).
- [ ] Exactly one obvious primary action for each exercise state.
- [ ] Correct and incorrect answers are visually distinguishable without
      relying on color alone (wording or icon as well).
- [ ] Loading and review indicators are never visible after the action they
      describe has completed.
- [ ] Sentence practice stays hidden until its step is reached.
- [ ] Progress is clearly visible but never dominates the exercise.
- [ ] Works on desktop and mobile with the same hierarchy.

### Accessibility floor (references never override this)

- Semantic HTML: real `button`, `form`, `label`, `fieldset`, headings in order.
- Full keyboard operation; Enter submits; nothing is reachable by mouse only.
- Visible focus states on every interactive element.
- WCAG AA contrast for text, in both light and dark color schemes.
- Every input has an associated label (it may be visually subtle, but it
  must exist).
- Touch targets of at least 44px on narrow layouts.

### Do not copy

Use references for principles only. Never bring into the product: logos,
trademarks, proprietary illustrations or icons, copyrighted text or any copy
from the reference, or brand-specific assets, including a brand's signature
colors used as identity. Never download or scrape a website. If the developer
names a site instead of giving a screenshot, work from general knowledge of
its design language or ask for a screenshot.

### Stop and ask

Stop and ask the developer before going on when:

- the redesign would change learning behavior: answer checking, word order,
  practice modes, confirmation steps, sentence review, progress tracking,
  voice input or feedback wording;
- no references are found (the folder is missing, or holds only `.gitkeep`).
  Offer to proceed with the hard rules alone;
- references conflict in a way that would materially change the page.

## 1. Gather inputs

- **Target page**: taken from the request, as a page key such as
  `vocabulary-practice`. Any key works. New pages just get a new folder.
- **Reference set**: every image in `design/references/<page>/`, plus
  everything in `design/references/shared/`, plus `notes.md` in either folder
  if present (the developer's intent wins over your reading of the images).
- **Code that renders the page**: find the template, stylesheet and script
  for that page (today, `src/web/templates/`, `src/web/static/`), and the
  tests that assert on them (`tests/unit/test_web_static_assets.py` and
  others that grep the template, CSS or JS).

## 2. Inspect references

View every reference image yourself. Work through
[reference-analysis.md](reference-analysis.md) for each one, then note where
they agree and where they conflict.

## 3. Understand the existing UI

Before proposing anything, read:

- the template structure and which elements each state shows or hides;
- the CSS custom properties in `:root` and its dark-mode block, and the
  existing classes;
- how the JS renders each state from the server, so you know which parts are
  presentation and which are behavior;
- the static-asset tests, so you know which class names, ids and wording are
  asserted.

## 4. Design interpretation

Fill in [design-interpretation.md](design-interpretation.md) and **show it to
the developer before editing any file**. It must list what is deliberately
not carried over from the references.

## 5. Implement

1. Run `pytest -q` and record the result as the baseline.
2. Use the existing stack: the Jinja template, plain CSS and vanilla JS. Never
   add a framework, build step or dependency, and never add one to
   `pyproject.toml`.
3. Extend existing CSS custom properties and classes before adding new
   ones. Update dark mode alongside light mode.
4. Change JS only for presentation (classes, element order, text placement).
   Never change what is sent to or done with the API.
5. Keep the `[hidden] { display: none !important; }` guarantee and every
   `hidden` toggle working.
6. If a static-asset test asserts on something you deliberately renamed,
   update the test and say so in the report. Don't silently weaken tests.
7. Run `pytest -q` again. It must match the baseline.

## 6. Verify visually

Follow [visual-verification.md](visual-verification.md): run an isolated
instance against the fixture vocabulary, drive it into each state the change
affects, and capture at 1280px and 390px. If no browser tooling works, say
plainly that visual verification was skipped and why. Never claim or imply a
check that didn't happen.

## 7. Refine

Compare each capture with the references and the interpretation using the
checklist in `visual-verification.md`. Fix every finding marked **fix** and
re-capture. Stop when none remain or after at most **3** refine passes. Don't
chase pixel matching at the cost of real content, usability, accessibility
or responsive behavior. Record such differences as intentional deviations
with a reason. Stop the verification server when done.

## 8. Report

End with:

- **References** used, and any skipped with the reason
- **Interpretation** (as shown in step 4)
- **Files changed**, with one line each on what changed
- **Tests**: baseline vs. final `pytest` result
- **Screenshots**: paths per pass and width, or "visual verification skipped:
  <reason>"
- **Fixes** made in each refine pass
- **Intentional deviations** from the references, with reasons
- **Remaining differences** after the final pass
