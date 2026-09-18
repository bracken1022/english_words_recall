# Phase 0 Research: Fix Web UI State Visibility

## Root cause, confirmed by reading the shipped code

- **Finding**: `src/web/static/style.css` contains:

  ```css
  section {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  ```

  and

  ```css
  .spinner {
    display: flex;
    align-items: center;
    gap: 10px;
    ...
  }
  ```

  Every step `<section>` (`empty-view`, `complete-view`, `recall-view`,
  `sentence-view`, `feedback-view`) and the spinner `<div>` also carry the
  HTML `hidden` boolean attribute, toggled correctly by `app.js`
  (`showOnly(step)` sets `el.hidden = name !== step`; the spinner is set
  directly). The HTML Living Standard gives `hidden` an implicit `display:
  none` **only via the user-agent stylesheet**. An **author** stylesheet
  rule that sets `display` on the same element — exactly what `section
  {...}` and `.spinner {...}` do — takes precedence over the user-agent
  rule regardless of selector specificity, because author-origin styles
  outrank user-agent-origin styles in the CSS cascade. The practical
  result: `hidden` has had **no visual effect** on any of these elements
  since they were first styled — every step's content, plus the spinner,
  has been rendered simultaneously the entire time, even though `app.js`'s
  own state logic and the DOM's `hidden` property were both already
  correct.
- **Why this matches all four reported symptoms**: the "no items" and
  "session complete" `<section>`s are subject to the exact same rule, so
  they've been visible from the very first page load regardless of the
  actual step — which is why they read as "always there" to the reporter.
  The recall/sentence sections being simultaneously visible, and the
  spinner being permanently visible, are the same mechanism.
- **Why `003`/`004`'s automated tests didn't catch this**: every existing
  test that touches this ("recall step hides English", "spinner toggles",
  the `004` state-machine tests) asserts against the DOM's `hidden`
  boolean or the server's JSON `step` field — both of which were, and
  still are, correct. None of them render the page in an actual browser
  engine and check computed style, so none could observe the CSS override.
  This is the same category of gap `003`'s own research.md already flagged
  ("Testing the web layer without a real browser") — it's now shown to
  have a real cost, not just a theoretical one.

## The fix: restore `[hidden]`'s guarantee with one rule

- **Decision**: Add one rule, placed after the `section`/`.spinner` rules
  it needs to override (or anywhere, given `!important` makes source order
  moot except versus other `!important` rules, of which there are none in
  this file):

  ```css
  [hidden] {
    display: none !important;
  }
  ```

- **Rationale**: This is the standard, widely-documented fix for exactly
  this browser behavior (an author `display` rule defeating the `hidden`
  attribute) — `!important` here is the textbook-correct use of the
  escape hatch: enforcing a boolean HTML-semantic state ("this element is
  not part of the document's current rendering") that must never lose to
  an ordinary presentational rule, rather than papering over unrelated
  specificity fights. A global, attribute-selector rule also means any
  future element in this app that uses `hidden` gets the same guarantee
  automatically, without needing a per-selector patch (`section[hidden]`,
  `.spinner[hidden]`, and so on) every time a new toggled element is added.
- **Alternatives considered**: Scoping the override narrowly —
  `section[hidden], .spinner[hidden] { display: none; }` (no
  `!important`, relying on specificity: `0,2,0` beats `section`'s `0,0,1`
  and ties `.spinner`'s `0,1,0`, needing source-order-after placement to
  win the tie) — rejected as more fragile long-term: it silently stops
  working the moment a future rule adds display to a third element that
  isn't enumerated here, recreating this exact bug. Reworking visibility
  to a class-based system (`.step { display: none }` /
  `.step.is-active { display: flex }`, with `app.js` toggling a class
  instead of `.hidden`) — rejected as a much larger change than this bug
  warrants: it would touch `app.js`, `index.html`'s classing, and every
  test that currently asserts on `.hidden`, for a fix that a single CSS
  rule already fully solves, directly violating this feature's own
  constraint (FR-008 / plan.md Constraints) to make the smallest change
  that restores the already-specified, already-tested behavior.

## Testing this without browser automation

- **Decision**: Add a regression-guard test asserting `style.css` contains
  a rule targeting `[hidden]` that sets `display: none` with `!important`
  — i.e., checking that the *mechanism* of the fix is present, the same
  static-content-assertion style `004` already established for CSS
  claims (`.feedback-correct`, `.field-row`, etc.). Real on-screen
  rendering is verified by hand in `quickstart.md`.
- **Rationale**: A static assertion can't prove the cascade resolves
  correctly in every browser, but it does two things well: it fails
  immediately if someone removes the fix later (the actual regression this
  bug represents), and it's consistent with `003`'s explicit,
  previously-made decision not to introduce browser automation tooling for
  this project. Given that decision is what let this bug ship unnoticed,
  the honest trade-off is documented here rather than silently repeated:
  manual verification in `quickstart.md` is the only way this feature's
  actual visual claims (SC-001 through SC-005) get proven, and that step
  must not be skipped for this feature specifically.
- **Alternatives considered**: Introducing a headless-browser test (e.g.,
  Playwright) just for this fix — rejected as disproportionate: it would
  be the first browser-automation dependency in the project, added
  reactively for one bug, in a codebase that already has an established,
  deliberate reason not to have one (`003-web-ui/research.md`). If this
  class of bug recurs, that decision is worth revisiting as its own
  discussion — not smuggled in as a side effect of this fix.
