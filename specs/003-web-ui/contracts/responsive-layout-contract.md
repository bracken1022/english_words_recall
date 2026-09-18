# Contract: Responsive Layout

Implemented by `src/web/static/style.css` and `templates/index.html`.
Covers FR-016, SC-003.

## Breakpoint contract

| Viewport width | Layout |
|---|---|
| Below the tablet breakpoint (phone-width, e.g., < 600px) | Single-column, full-width content with side padding; no fixed-width elements wider than the viewport; touch-sized inputs/buttons (minimum comfortable tap target). |
| Tablet width and above (e.g., ≥ 600px) | Content area gains a `max-width` and is centered; otherwise the same single-column structure — no multi-column layout is introduced at any width. |

- **Rule**: no element or combination of elements may cause horizontal
  scrolling at any width from phone-width upward (FR-016, SC-003). This is
  the one thing `quickstart.md`'s manual check must explicitly verify,
  since it is not practical to assert via an HTTP-level automated test.
- **Rule**: the layout is mobile-first — base (unprefixed) CSS rules target
  the narrowest supported width; wider layouts are reached via `min-width`
  media queries that relax constraints, not the other way around (per
  `research.md`'s rationale).

## Content contract

At every width, the page always shows exactly one of: the recall prompt
(Chinese meaning + answer input), the sentence prompt (accepted expression
already revealed + sentence input), the loading indicator (per
`loading-indicator-contract.md`), or the feedback/continue view — never two
of these stacked ambiguously, and never a scroll required to reach the
input or the continue action for the current step.

## Out of scope for this contract

- Pixel-exact visual design (colors, fonts) — not specified by the spec
  beyond "simple."
- Landscape-vs-portrait-specific layouts — the same rules apply regardless
  of device orientation; no separate contract is defined for orientation.
