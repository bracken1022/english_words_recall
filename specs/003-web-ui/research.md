# Phase 0 Research: Web UI for Remote Access

## Web framework: Flask

- **Decision**: Use Flask, with its bundled Jinja2 for the single HTML
  template and Flask's development server (`app.run(host="0.0.0.0",
  port=...)`) as the process the learner starts manually.
- **Rationale**: The workload here is genuinely simple — one page, three
  small JSON endpoints, no concurrency requirement (spec.md Assumptions:
  one shared session, simultaneous multi-device use is explicitly
  unsupported). Flask is minimal, ubiquitous, needs no async runtime, and
  its dev server binding to `0.0.0.0` is exactly "reachable on the LAN, not
  the public Internet by default" (FR-013/FR-015) with zero extra
  configuration. Using Flask's own dev server for a non-production,
  personal, LAN-only tool is an accepted tradeoff explicitly scoped by the
  spec ("no cloud deployment," "not exposed to the public Internet by
  default") — this is not a production Internet-facing deployment.
- **Alternatives considered**: FastAPI + uvicorn — rejected: its async
  model buys nothing here (the one slow call, `request_correction`, is a
  blocking `requests.post` either way, and there is no concurrency
  requirement to justify an async server) while adding a second dependency
  and a different mental model from the rest of this synchronous codebase.
  Plain `http.server` — rejected: would mean hand-rolling routing, JSON
  body parsing, and templating that Flask already provides correctly and
  simply.

## Frontend approach: server-rendered shell + vanilla JS, no build step

- **Decision**: One Jinja2-rendered HTML page (`templates/index.html`)
  containing the recall/sentence/feedback UI regions (shown/hidden by JS
  depending on state), a plain CSS file with a mobile-first responsive
  layout, and a plain JS file using `fetch()` against the JSON endpoints.
  No JS framework, no bundler, no npm dependency.
- **Rationale**: The spec asks for "simple and responsive," not a rich
  single-page app — a build step would be pure overhead for three
  endpoints and one page. `fetch()` plus showing/hiding a few DOM regions
  is enough to implement the whole recall → sentence → feedback → next
  loop, and is exactly what's needed to implement FR-007's loading
  indicator (see below).
- **Alternatives considered**: A JS framework (React/Vue/etc.) with a
  bundler — rejected as unwarranted complexity for this scope, and it would
  introduce a second toolchain (npm) into a project that is otherwise pure
  Python. Full-page reloads per step (no JS at all) — rejected: it cannot
  show a spinner *during* the wait for `/api/sentence` (the whole point of
  FR-007) without JavaScript, since a full-page reload can only show
  something *after* the response arrives, not while it's pending.

## Loading indicator: JS spinner scoped to the one slow request

- **Decision**: The client shows a visible, CSS-animated indeterminate
  spinner element the instant the `/api/sentence` `fetch()` call is issued,
  and hides it in that fetch's completion handling (covering both the
  success and error/network-failure paths), before rendering whatever
  result came back. No percentage or step count is ever computed or shown,
  because none is available (mirrors `002-sentence-review-indicator`'s
  FR-004, now in the browser).
- **Rationale**: This is the same behavioral contract already established
  and tested for the CLI in `002` (appear immediately, span the whole
  wait, disappear on completion or failure, no fabricated progress) — the
  *mechanism* has to differ (there is no terminal/`rich` in a browser), but
  the *contract* carries over directly. Scoping it to only the
  `/api/sentence` request (not `/api/answer` or `/api/continue`, which are
  fast, local, non-LLM calls) matches `002`'s finding that only the LLM
  call is slow enough to need one.
- **Alternatives considered**: A server-sent-events or WebSocket-based
  "typing…" style progress stream — rejected: `request_correction` has no
  intermediate progress to stream (it's one blocking HTTP call to Ollama),
  so a streaming channel would carry nothing more than the same "still
  waiting" signal a spinner already provides, for real added complexity.

## Session/state model: one shared, in-memory `PracticeSession`

- **Decision**: A single `PracticeSession` object lives for the lifetime of
  the running server process (not per-cookie, not per-visitor). It holds
  the filtered `VocabularyItem` list, the current index, the current step
  (`recall` / `sentence` / `feedback` / `complete` / `empty`), and the
  in-progress `PracticeAttempt` draft (recall answer + correctness captured
  at the recall step; sentence + feedback added at the sentence step,
  exactly mirroring `session.py`'s local variables in `001`/`002`, just
  held across HTTP requests instead of within one function call).
- **Rationale**: spec.md's Assumptions already settled this: single shared
  session, simultaneous multi-device use undefined/unsupported. A
  process-global object is the simplest thing that satisfies that — no
  cookies, no session store, no per-request identity, which also keeps
  FR-014 (no auth) trivially true rather than something to actively avoid
  building.
- **Alternatives considered**: Flask's built-in cookie-based sessions (one
  `PracticeSession` per browser) — rejected: this would let two devices
  each have their own independent walk through the vocabulary pool
  concurrently, which is a bigger feature (effectively multi-user) than
  what's in scope, and spec.md explicitly calls simultaneous multi-device
  use unsupported/undefined rather than asking for isolated per-device
  sessions.

## Lesson/tag filtering: server-startup flag, not an in-page picker

- **Decision**: `python -m src.web --group unit1` filters the pool at
  server startup, exactly like the CLI's existing `--group` flag — there is
  no in-browser control to change the filter after the server is running.
- **Rationale**: spec.md's Assumptions require existing filtering to
  "remain available in some form," not that a new UI be built for it. A
  startup flag reuses the exact mechanism `001-vocab-recall-tutor` already
  has (`vocabulary_loader`'s filtering, already unit-tested) with zero new
  UI surface, keeping this feature's scope to "add a web UI," not "add a
  lesson-management UI."
- **Alternatives considered**: An in-page dropdown to pick a lesson/group —
  rejected for this iteration as a larger feature than what was asked
  ("build a web UI" with the UX steps given, none of which mention
  choosing a lesson); it can be layered on later without conflicting with
  anything decided here.

## Responsive layout approach

- **Decision**: Mobile-first CSS: a single-column, generously-padded
  layout by default (assumes a narrow phone screen), widened/centered with
  a max content width via a media query for tablet/desktop widths. No
  horizontal scrolling at any width; form inputs and buttons sized for
  touch (per FR-016, SC-003).
- **Rationale**: Designing for the narrowest target first and progressively
  relaxing constraints for wider screens is the standard, simplest way to
  guarantee the narrow case works, rather than designing for desktop and
  trying to compress it down (which is where horizontal-scroll/overlap bugs
  usually come from).
- **Alternatives considered**: A desktop-first layout with `max-width`
  collapse — rejected: more prone to overlooking narrow-screen edge cases,
  which is exactly the failure mode FR-016/SC-003 exist to prevent.

## Testing the web layer without a real browser

- **Decision**: `pytest` + Flask's `app.test_client()` for every endpoint
  contract and integration test (posts JSON, asserts status code and
  response body; mocks `request_correction` exactly as `001`/`002` already
  do for the CLI). No browser automation (e.g., Selenium/Playwright) is
  introduced for this feature's automated suite.
- **Rationale**: The behavior that needs proving — correct grading, correct
  step sequencing, correct feedback fields, correct fallback on LLM
  failure, correct rejection of out-of-order requests — is all observable
  at the HTTP/JSON layer. The responsive-layout and spinner-visibility
  claims (FR-016, FR-007) are UI-rendering concerns best checked by hand in
  a real browser per `quickstart.md`, matching how `002` treated actual
  spinner *animation* (verified by hand, contract-tested for timing) rather
  than snapshot-testing rendered pixels.
- **Alternatives considered**: Browser automation for full end-to-end
  coverage — rejected as disproportionate setup/maintenance cost for a
  personal single-learner tool; the manual `quickstart.md` scenarios cover
  what automated HTTP-level tests structurally cannot (does it actually
  look right on a phone).
