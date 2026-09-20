# Research: Show a Correct Recall Result in Green

No open `NEEDS CLARIFICATION` markers — spec.md's Assumptions already
resolved scope, the accessibility safeguard, and left the exact shade as
a planning decision. This file records that decision and the reasoning.

## 1. Color values

**Decision**: Add two new tokens to `style.css`'s existing `:root`/dark
custom-property system, mirroring how `--red`/`--red-tint` are already
structured:

| Token | Light | Dark |
|---|---|---|
| `--green` | `#2f6d3a` | `#5fbd6e` |
| `--green-tint` | `#e3efe4` | `#1f3324` |

`.feedback-correct` gets its own rule overriding `color`/`background`/
`border-color` to these, layered on top of `#word-feedback`'s existing
base rule (which stays red — now effectively the incorrect/default
styling, since `.feedback-incorrect` needs no override at all).

**Rationale**: Matches the existing token pattern exactly (a saturated,
readable "ink" tone for light mode; a lighter, more saturated version for
dark mode, mirroring `--red: #a8281f` → `--red-tint: #f5e4e1` light and
`--red: #e5573e` → `--red-tint: #3a241f` dark). Both `--green` values keep
comfortable contrast against `--card` (`#fcfbf6` light / `#1b222b` dark) —
verified visually in the manual browser pass (`quickstart.md`), not just
computed, since this project has no automated contrast-checking tooling
and none is being added for one color pair.

**Alternatives considered**: Reusing a "success" green from a common UI
palette (e.g. a Bootstrap/Material green) — rejected as exactly the kind
of default-looking, unconsidered choice this project's design work has
otherwise avoided; the existing red was deliberately picked to match this
app's "notebook ink" aesthetic rather than a generic palette, and the new
green should be picked the same way, not borrowed from elsewhere.

## 2. Where the override lives

**Decision**: A new `.feedback-correct` rule directly below the existing
`#word-feedback::before`/`.feedback-correct::before`/`.feedback-incorrect::before`
block, setting only `color`, `background`, and `border-color` (not
`font-weight`, `padding`, `transform`, etc., which stay shared via
`#word-feedback`'s base rule).

**Rationale**: `#word-feedback`'s base rule already carries every
non-color visual property (stamp shape, rotation, padding, animation);
only the three color-related properties differ per outcome. Overriding
just those three keeps the rule minimal and makes the code's intent
obvious: correct and incorrect are the same *kind* of mark, just a
different ink.

**Alternatives considered**: Also adding an explicit (redundant)
`.feedback-incorrect` color rule pointing at `--red`/`--red-tint` for
symmetry — rejected as unnecessary; it would just restate the base rule's
existing values with no behavioral difference, and this project generally
avoids restating values that don't need to change (e.g. `006`'s
`.feedback-correct::before`/`.feedback-incorrect::before` split already
follows this same only-override-what-differs pattern).

## 3. Test strategy

**Decision**: One static-content assertion in
`tests/unit/test_web_static_assets.py`, matching this project's
established "no JS/browser test runner" convention (`005`/`006`/`007`):
parse `style.css`, find the `.feedback-correct { ... }` rule body, and
assert it references `--green` (not `--red`) — a regression guard against
someone reusing the same token for both classes again. A real-browser
pass (light and dark) remains the actual proof the color reads clearly
and legibly, per `quickstart.md` — a passing test only proves the *token*
changed, not that it looks right.

**Alternatives considered**: Introducing an automated visual/contrast-
ratio check (e.g. a headless-browser screenshot diff or a WCAG contrast
calculation in a test) — rejected as new tooling disproportionate to a
one-color-pair change; this project has never added browser automation to
its checked-in suite (see `006` research.md §5), and a manual pass already
covers this adequately at this scale.
