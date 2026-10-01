# Contract: Visual verification recipe

This is the canonical content of `.claude/skills/frontend-design/visual-verification.md`.

## 1. Start an isolated instance

```sh
python -m src.web --vocab-dir design/fixtures/vocabulary \
  --progress-file design/verification/progress.md \
  --host 127.0.0.1 --port 8421
```

Run it in the background. Wait until `curl -s localhost:8421/api/state` responds.
Stop it when done.

## 2. Drive state via the API (then load/reload `/`)

| State | Calls (from a fresh server) |
|-------|-----------------------------|
| choose | none |
| recall | `POST /api/select {"collection":"design-fixture","order":"sequential","mode":"sentence"}` |
| sentence (after correct) | recall + `POST /api/answer {"answer":"<first fixture word>"}` |
| reveal / wrong (recall-only) | select with `mode:"recall-only"` + `POST /api/answer {"answer":"zzz"}` |
| feedback | sentence + `POST /api/sentence {"sentence":"..."}` (shows unavailable-feedback if Ollama is down) |
| complete | answer/skip/continue through all fixture words |

Body field names must match `src/web/app.py`. Check them before use; the code is the
source of truth. Restart the server to reset state.

## 3. Capture

Viewports 1280×800 and 390×844, full page. Save as
`design/verification/<page>/pass-<N>/<state>-<width>.png`.

Tooling ladder:
1. Claude browser tools present → load the matching browser skill, navigate, resize,
   screenshot. Also watch transient states (loading/review spinners) disappear after
   completion.
2. Else `npx -y playwright screenshot --viewport-size=1280,800 --full-page URL FILE`
   (one-time `npx -y playwright install chromium` if it fails).
3. Else report: "Visual verification skipped: <reason>". Give the commands above so the
   developer can check by hand.

## 4. Compare

View the reference(s) and the capture together. For each category (spacing, sizing,
alignment, typography, density, hierarchy, component consistency, state correctness,
accessibility/contrast/focus) record *fix*, *intentional (reason)* or *matches*.
Compare against the **interpretation**, not pixels.

## 5. Loop

Fix all *fix* items → pass N+1. Stop when there are none, or after pass 3, then report
what remains.
