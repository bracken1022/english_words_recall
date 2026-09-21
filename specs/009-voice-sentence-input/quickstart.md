# Quickstart: Speak Your Sentence Instead of Typing It

Validates that the feature described in `spec.md` works end-to-end, once
implemented per `plan.md`/`tasks.md`.

## Prerequisites

```bash
cd english-tutor
.venv/bin/pip install -e ".[dev]"

# Voice input is optional (FR-007) — install it deliberately to test it:
.venv/bin/pip install -e ".[voice]"
```

The first time voice input is actually used, `faster-whisper` downloads
and caches a small Whisper model (a one-time step requiring internet
access, the same kind of one-time setup as `ollama pull qwen3:14b` —
this is *setup*, not the app talking to the network during practice).
To pre-warm the cache before testing so the first request in Scenario 1
isn't slow:

```bash
.venv/bin/python -c "from faster_whisper import WhisperModel; WhisperModel('base')"
```

A small scratch vocabulary, reused from earlier quickstarts:

```bash
mkdir -p /tmp/voice-quickstart-vocab
cat > /tmp/voice-quickstart-vocab/one.md <<'EOF'
---
english: receive
alternates: [accept]
chinese: 收到；接受
---
EOF
```

## Run

```bash
.venv/bin/python -m src.web \
  --vocab-dir /tmp/voice-quickstart-vocab \
  --progress-file /tmp/voice-quickstart-progress.md \
  --group unit1 --port 8420
```

(`--group` here just skips the `007` collection-choice screen to reach
the recall/sentence steps quickly — irrelevant to this feature.)

Open `http://localhost:8420/` — voice capture requires a secure context,
so this only works when opened on **the same machine** running the
server (`localhost`), not from another device's browser at a LAN
address (spec.md Assumptions).

## Validation scenarios

### 1. Voice input transcribes into the sentence field (US1, FR-001–FR-002)

1. Answer the recall step, reaching the sentence-writing step.
2. **Expected**: a microphone control is visible next to the sentence
   input (`voice_available: true` in `GET /api/state`).
3. Start voice input, say a sentence using the target word out loud, then
   stop.
4. **Expected**: a transcribing indicator appears briefly (reusing the
   existing spinner style), then the sentence field is populated with the
   recognized text — editable, not yet submitted.

### 2. Typing still works, and review/edit before submit (FR-002, FR-003)

1. Edit the transcribed text (fix any misheard words), then submit.
2. **Expected**: behaves exactly as if that text had been typed — the
   existing "Reviewing your sentence..." spinner and correction feedback
   appear as usual.
3. Start a fresh sentence step and type instead of using voice.
4. **Expected**: no change at all from before this feature.

### 3. Graceful fallback when voice isn't available (FR-004, FR-007)

1. Stop the server, `pip uninstall faster-whisper` (or run in a venv
   without it installed), and restart.
2. **Expected**: the app starts normally; `GET /api/state` reports
   `voice_available: false`; no microphone control appears anywhere;
   typing works exactly as before this feature existed.

### 4. Privacy: nothing leaves the machine, nothing is retained (FR-005, FR-006, SC-004)

1. With voice available again, open the browser's network inspector
   while performing Scenario 1.
2. **Expected**: the only request carrying the recorded audio is
   `POST /api/transcribe` to this app's own origin — no request to any
   third-party host.
3. **Expected**: no new file appears on disk after transcribing (check
   the working directory and any obvious temp-file location) — the audio
   existed only in memory for the duration of that one request.

## Automated coverage

- `tests/unit/test_speech_client.py` — transcription result shape and
  failure handling, with the model call mocked
- `tests/contract/test_web_api_contract.py` — `POST /api/transcribe` and
  `voice_available` HTTP contract
- `tests/integration/test_web_session_flow.py` — full record → transcribe
  (mocked) → review → submit flow
- `tests/unit/test_web_static_assets.py` — static assertion that `app.js`
  wires up recording/upload/mic-visibility

```bash
.venv/bin/pytest -q
.venv/bin/ruff check src/
```

Both MUST pass, and Scenarios 1–4 MUST be run in a real browser (voice
capture cannot be exercised by the automated suite at all), before this
feature is considered done.
