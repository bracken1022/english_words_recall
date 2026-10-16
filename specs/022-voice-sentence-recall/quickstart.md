# Quickstart: Validate Voice Answers for Sentence Recall

Use temp copies of learner data for every manual check: never the real
`vocabulary/`, `word-lists/` or `progress.md`.

## Prerequisites

- `pip install -e '.[voice]'` (installs `faster-whisper`; the `base`
  model downloads once, about 150 MB).
- Ollama running, for examples. A word with a saved example makes the
  checks quicker.
- Chrome or Safari on the Mac itself (`http://localhost:8420`), so the
  page is allowed to use the microphone.

## Automated

```sh
.venv/bin/python -m pytest -q
.venv/bin/ruff check src tests
```

Covers: the word-diff fixture (SC-007), `/api/transcribe` statuses and
step guard, no audio written to disk, reveal with `attempt` and
`comparison`, `voice_available`, the history writing only the mark
(SC-006), and the page wiring.

## Manual scenarios

| # | Scenario | Expected |
|---|---|---|
| a | Mode "Recall + example + sentence recall"; answer a word; at sentence recall tap Speak, read the sentence, tap Stop | Text appears in the box within 3 s (SC-001); nothing is revealed |
| b | Edit the text, then Show sentence | Your edited attempt shows; missing words underlined, extra words struck through; you still choose Got it / Not yet |
| c | Type "She is", then Speak the rest | Spoken text is added after "She is" |
| d | Speak nothing for 5 s, Stop | "Didn't catch that" note; box unchanged |
| e | Let a recording run 30 s | It stops by itself and transcribes |
| f | Start recording, then Skip | Recording stops; nothing uploaded (no `/api/transcribe` in the network tab) |
| g | Block the microphone in the browser, tap Speak | Blocked note; typing still works |
| h | Uninstall the extra (or run a venv without it) | No mic button; sentence recall works by typing |
| i | Open the app from a phone at `http://<mac-ip>:8420` | No mic button, with the "needs this page on the Mac" note; typing works |
| j | After a session, look in the temp data folder and `/tmp` | No audio files; `progress.md` has only `sentence_recall` marks, no attempt text |
| k | Word recall step | No mic button |

## Recognition accuracy (SC-002)

1. Record yourself (or a learner, with their consent) reading 20 example
   sentences clearly, one file per sentence, into
   `backups/voice-022-eval/`, with `sentences.yml` mapping file name to
   sentence. For a quick smoke test, `say -o clip.aiff "…"` works too.
2. `python -m src.tools.eval_voice backups/voice-022-eval`
3. Pass: word accuracy ≥ 90% and every clip transcribed in under 3 s.
   Record the result in `eval-report.md`. If `base` falls short, try
   `--model small` (research R1).

## Results — 2026-10-15

Run against temp data (scratchpad copy, never real learner data) with the
real local Whisper (`base`, `int8`) and examples faked; Chromium driven by
Playwright with a fake microphone playing a `say` recording
("She is zealous about recycling.").

| # | Result |
|---|---|
| a | PASS — text in the box 0.31 s after Stop ("She is jealous about recycling."); hint shown; nothing revealed |
| b | PASS — edited attempt revealed with `is` underlined and `was`, `plastic` struck; guide note; learner marks |
| c | PASS — spoken text added after "Typed first." |
| d | PASS — silence gives "Didn't catch that…"; box unchanged |
| e | PASS — stopped by itself at 30.0 s; 30 s clip transcribed in 4.4 s |
| f | PASS — Skip mid-recording: 0 uploads |
| g | PASS — blocked microphone (simulated `NotAllowedError`) shows the note; typing and reveal work |
| h | PASS — server without the extra: no Speak button; typing and reveal work |
| i | PASS — insecure page (simulated `isSecureContext = false`, 390 px wide): no Speak button, note shown, no horizontal scroll |
| j | PASS — only `progress-lily.md`, the vocab file and `.examples.json` in the temp data; no audio files in the temp dirs; the history has `sentence_recall` marks and no attempt or transcript text; the server log has request lines only, no recognised text |
| k | PASS — no Speak button at word recall |

Automated: 1179 tests pass; `ruff check src tests` clean.
