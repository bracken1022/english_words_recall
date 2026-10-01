# Visual verification recipe

Check the implemented page against the references and the design
interpretation, then refine it. Compare against the **interpretation**, not
pixels.

## 1. Start an isolated instance

Never run against the learner's real `vocabulary/` or `progress.md`.

```sh
python -m src.web --vocab-dir design/fixtures/vocabulary \
  --progress-file design/verification/progress.md \
  --host 127.0.0.1 --port 8421
```

Run it in the background (create `design/verification/` first if it doesn't
exist). Wait until `curl -s http://127.0.0.1:8421/api/state` responds. Stop the
server when verification ends. Port 8421 avoids clashing with a developer's
own instance on 8420.

## 2. Drive the page into each state

The server holds one shared practice session, and the page renders whatever
`GET /api/state` returns. So call the JSON API with `curl`, then load or
reload `/` to screenshot that state. Restart the server to reset.

| State | Calls from a fresh server |
|-------|---------------------------|
| choose | none |
| recall | `POST /api/select` `{"collection": "design-fixture", "order": "sequential", "mode": "sentence"}` |
| sentence step (after a correct answer) | recall, then `POST /api/answer` `{"answer": "<first fixture word>"}` |
| wrong answer awaiting confirmation | select with `"mode": "recall-only"`, then `POST /api/answer` `{"answer": "zzz"}` |
| sentence feedback | sentence step, then `POST /api/sentence` `{"sentence": "..."}`. Shows "feedback unavailable" if Ollama is not running, which is a real state too |
| complete | answer, `POST /api/skip` or `POST /api/continue` until every fixture word is done |

Field names must match the routes in `src/web/app.py`. Read them before use,
because the code is the source of truth. Only capture the states the change
affects, plus the default state.

## 3. Capture

Viewports: **1280×800** (desktop) and **390×844** (narrow/mobile),
full page. Save to
`design/verification/<page>/pass-<N>/<state>-<width>.png` (pass 0 is the first
capture after implementing).

Use the first tool that works:

1. **Claude browser tools in this session**: the built-in browser
   (`mcp__Claude_Browser__*`) or Claude in Chrome (`mcp__claude-in-chrome__*`).
   Load `anthropic-skills:built-in-browser` or `anthropic-skills:chrome-browser`
   first. Navigate, resize the viewport for each width, screenshot. Because
   these tools can interact, also submit an answer and watch the loading or
   review indicator appear and then **disappear** once the result arrives.
2. **Playwright CLI** (fetched by npx, never added to the project):
   `npx -y playwright screenshot --viewport-size=1280,800 --full-page http://127.0.0.1:8421/ <file>`.
   If the browser is missing, run `npx -y playwright install chromium` once.
   This tool can't watch transient states, so check by reading the JS and CSS
   that loading and review indicators are hidden when the request completes
   (the `[hidden]` rule must still win), and say in the report that this was
   checked by reading the code.
3. **Neither available**: report `Visual verification skipped: <reason>` and
   give the developer the commands from §1–3 to run the check by hand. Never
   describe or imply screenshots that weren't taken.

Open each capture you take and actually look at it.

## 4. Compare

Put each capture next to the relevant reference(s) and the interpretation.
Record one line per category, marking it **fix**, **intentional (reason)** or
**matches**:

- **Spacing**: gaps between groups, padding inside controls, rhythm
- **Sizing**: prompt, input and button sizes relative to the interpretation
- **Alignment**: shared edges and axes, centered vs. left
- **Typography**: number of levels, size ratios, weights
- **Density**: too crowded or too sparse compared with the reference's feel
- **Hierarchy**: whether the current exercise is the first thing seen and
  the primary action is obvious, at **both** widths
- **Component consistency**: buttons, inputs and feedback styled alike
  across states
- **State correctness**: correct and incorrect are clearly different;
  nothing stale stays visible; sentence practice is hidden until its step
- **Accessibility**: contrast, visible focus, target size at 390px, no
  horizontal scroll

Mark an item intentional, not fix, when matching the reference would hurt real
content, usability, accessibility or responsive behavior.

## 5. Loop

Fix every **fix** item, re-capture as `pass-<N+1>`, and compare again. Stop
when no **fix** items remain or after **3** refine passes, whichever comes
first, then report what still differs and why.
