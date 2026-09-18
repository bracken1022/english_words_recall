# Contract: The `hidden` Attribute Actually Hides

Implemented by `src/web/static/style.css`. Covers spec FR-001 through
FR-007. This is a correction to a guarantee `003-web-ui`'s
`loading-indicator-contract.md` and `004-web-ui-ux-polish`'s
`ui-rendering-contract.md` already assumed held — it does not change what
either of those contracts specifies, it makes it actually true.

## The guarantee

Any element in `templates/index.html` carrying the HTML `hidden` boolean
attribute MUST NOT be visually rendered, **regardless of any other CSS
rule** that sets `display` on that element via a tag, class, or ID
selector. This holds for every current toggled element (`empty-view`,
`complete-view`, `recall-view`, `sentence-view`, `feedback-view`,
`spinner`) and for any element added later that follows the same
`el.hidden = true/false` convention already established in `app.js`.

## What this restores (not changes)

| Contract | Claim it already made | Now actually true |
|---|---|---|
| `003-web-ui/contracts/loading-indicator-contract.md` | The spinner is hidden outside an in-progress review | Yes — the spinner's `hidden` attribute now actually removes it from rendering |
| `004-web-ui-ux-polish/contracts/ui-rendering-contract.md` | Exactly one step's primary area is shown at a time (the single-primary-area rule) | Yes — a step's `<section hidden>` now actually removes it from rendering |

No field, endpoint, or JSON shape changes. This contract is purely about
what the browser paints for a given, already-correct `hidden` state.

## Out of scope for this contract

- Any change to how `app.js` decides which element to hide (unchanged,
  already correct).
- Any change to the JSON `GET /api/state` contract (unchanged).
