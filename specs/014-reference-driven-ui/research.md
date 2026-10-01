# Research: Reference-Driven UI Design Workflow

## R1. Where the skill lives and how it relates to the plugin skill of the same name

- **Decision**: Fill in the existing, empty `.claude/skills/frontend-design/SKILL.md` with
  frontmatter `name: frontend-design`. The skill opens by saying it is the
  English Tutor project's workflow. It may use the general `frontend-design:frontend-design`
  plugin skill for aesthetic judgement, but its own rules take precedence.
- **Rationale**: The spec fixes the path. The plugin skill is namespaced
  (`frontend-design:frontend-design`), so the two don't collide. Making the precedence
  explicit stops the generic "be bold and distinctive" guidance from overriding the
  learning UI rules: focus on the exercise, no decoration.
- **Alternatives considered**: A different name such as `reference-ui`. Rejected because
  the spec and the developer's success-criterion phrasing both say "frontend-design skill".

## R2. Keeping the skill reusable and page-independent

- **Decision**: `SKILL.md` holds only the ordered methodology, the hard rules (learning UI,
  accessibility, do-not-copy, preserve behavior) and the stop condition. Three sibling
  files hold the long checklists, loaded when that step is reached. Page names appear
  only to explain the folder convention. Inputs are resolved at run time from the
  request: target page → `design/references/<page>/` + `shared/` → the template/CSS/JS
  that render it.
- **Rationale**: This meets FR-007 and SC-006. A second page needs a new folder, not a
  skill edit. Splitting the files keeps the always-loaded part small.
- **Alternatives considered**: One large file. Rejected because the checklists would
  crowd out the rules. Per-page sub-skills. Rejected because that is exactly the
  page-specific coupling the spec forbids.

## R3. Browser tooling for screenshots

- **Decision**: Use a capability ladder, picking the first that works:
  1. Claude browser tools already in the session (built-in browser `mcp__Claude_Browser__*`
     or Claude in Chrome `mcp__claude-in-chrome__*`). Load the matching skill
     (`anthropic-skills:built-in-browser` / `anthropic-skills:chrome-browser`) first.
     Resize the viewport for each width.
  2. `npx playwright screenshot --viewport-size=W,H --full-page URL out.png`. Node/npx
     is present on this machine. Run `npx playwright install chromium` once if needed.
     Nothing is added to the project.
  3. Neither is available: report "visual verification skipped" with the manual steps
     (FR-021).
- **Rationale**: The spec says "when browser tooling is available" and puts a
  visual-regression platform out of scope. Playwright's CLI needs no project code or
  dependency. The Python `playwright` package is not installed and is deliberately not
  added.
- **Alternatives considered**: Adding `playwright` to `pyproject.toml` dev deps. Rejected
  under FR-008 because it isn't needed. A headless-Chrome shell script. Rejected because
  it's more fragile than the Playwright CLI.

## R4. Reaching each UI state for screenshots without writing UI test code

- **Decision**: Drive state through the existing JSON API, then load or reload the page.
  `PracticeSession` is one shared object per server process, and `app.js` renders
  whatever `GET /api/state` returns, so `curl -X POST /api/select|answer|skip|continue`
  followed by a screenshot of `/` captures that state. The recipe lists the call sequence
  for: choose, recall (empty input), correct-result, wrong-result (recall-only, awaiting
  confirm), sentence step, complete.
- **Rationale**: No new code, deterministic, and it works with the plain Playwright CLI,
  which cannot click. With interactive browser tools, clicking through is also fine.
- **Alternatives considered**: A Playwright script that clicks through. Rejected because
  it's new code for little gain. Loading and spinner states are transient. With
  interactive tools Claude watches them appear and then disappear. With the CLI fallback
  this is checked by reading `app.js`/CSS (`[hidden]` rule), and the report says so.
- **Note**: The sentence *feedback* state needs Ollama. If it isn't running, the API
  returns `available: false` feedback, which is itself a real state worth screenshotting.
  The recipe doesn't require Ollama.

## R5. Isolating verification from learner data

- **Decision**: Run `python -m src.web --vocab-dir design/fixtures/vocabulary
  --progress-file design/verification/progress.md --port 8421 --host 127.0.0.1`.
  The fixture holds about 4 words in the existing YAML-block format, including one
  multi-alternate entry, in a single group `design-fixture`.
- **Rationale**: Constitution III. Port 8421 avoids clashing with a developer's running
  instance on 8420. Binding to 127.0.0.1 avoids exposing it on the LAN.
- **Alternatives considered**: Pytest `tmp_path`. Not applicable because verification
  isn't a pytest run. Using the real vocabulary. Rejected because it would write to
  progress.md.

## R6. Viewports

- **Decision**: Desktop 1280×800 and mobile 390×844, full-page captures.
- **Rationale**: Matches the spec's assumption. 390 is a common phone width and narrower
  than the current `.sheet` layout, so it shows wrapping or overflow.

## R7. Comparing and stopping

- **Decision**: Compare by viewing both images and filling in a fixed difference checklist
  (spacing, sizing, alignment, typography, density, hierarchy, component consistency,
  state correctness, accessibility). Classify each item as *fix*, *intentional deviation
  (reason)* or *matches*. Stop when no *fix* items remain or after 3 refine passes, then
  report.
- **Rationale**: FR-017, FR-019, FR-020. No pixel diffing (out of scope; it would also
  reward copying).

## R8. Testing a methodology document under Test-First

- **Decision**: Use static contract tests in the style of `test_web_static_assets.py`:
  - The skill has YAML frontmatter with `name` and `description`, contains each
    methodology step heading in order, contains the learning UI rules, accessibility
    rules and do-not-copy list, mentions the 3-pass cap and the skipped-verification
    statement, and links to the 3 sibling files, which exist.
  - The skill contains no page-specific selectors (`#recall-view`, `#answer-input`, …).
    This is the FR-007 guard.
  - The four reference folders and `design/README.md` exist. `/design/verification/` is
    git-ignored.
  - No file under `src/` contains the string `design/`. The Flask app built from
    `create_app` with a tmp vocab dir serves `/` and `/static/style.css` with status 200
    while the cwd is a tmp directory with no `design/` (SC-004).
- **Rationale**: These are the testable parts of the spec. Workflow *quality* is shown by
  the first real redesign, which is out of scope here.
