# Implementation Plan: Voice Answers for Sentence Recall

**Branch**: `022-voice-sentence-recall` | **Date**: 2026-10-15 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/022-voice-sentence-recall/spec.md`

## Summary

In the web app's sentence-recall step, the learner can tap "Speak", say
the sentence, and get the words it hears added to the attempt box, where
they can edit them before revealing. Recognition runs on the learner's
own Mac with local Whisper (`faster-whisper`, `base`, English), restored
from spec 009 as an optional extra; audio is decoded in memory and
dropped. At reveal, the page sends the attempt once; the server compares
it word by word with the real sentence (ignoring capitals and
punctuation) and returns which words are missing or extra, which the page
highlights. The learner still marks "Got it" / "Not yet"; only that mark
is saved. The rules are written down device-independently so a future
iPhone app can follow them with Apple's on-device recogniser.

## Technical Context

**Language/Version**: Python 3.11+ (server); vanilla JavaScript, HTML,
CSS (page)

**Primary Dependencies**: Flask (existing); `faster-whisper>=1.0` as the
optional `voice` extra (restored); Python standard library `difflib`

**Storage**: None new. Audio and attempts are never stored; the practice
history keeps only the spec 021 mark.

**Testing**: pytest (unit, contract, integration), ruff; the recogniser
is faked in tests (`conftest.py` keeps blocking real model calls)

**Target Platform**: The local web app (`python -m src.web`, served from
the learner's Mac); Chrome and Safari for recording. CLI unchanged.

**Project Type**: Single Python project with a web UI (`src/web`)

**Performance Goals**: Transcript in the box within 3 s of stopping for a
sentence of up to 20 words (SC-001); model preloaded at startup

**Constraints**: Local-only recognition (FR-004); no audio on disk or in
logs (FR-005); 30 s recording limit (FR-007); 1 MB request limit;
microphone only on secure pages (`localhost` or `https`)

**Scale/Scope**: A family's few accounts on one Mac; one recording at a
time per page

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | How this plan satisfies it | Status |
|---|---|---|
| I. Test-first | Every task in `tasks.md` starts with failing tests: the word-diff fixture, the speech client (faked model), `/api/transcribe` contract (statuses, step guard, no file written), reveal with `attempt`/`comparison`, `voice_available`, the history writing only the mark, and the page wiring. | Pass |
| II. Pedagogical accuracy & safety | The comparison is checked against a reviewed fixture (`tests/fixtures/word_diff_cases.yml`, SC-007), including its known limits. It is labelled a guide; the learner always marks (FR-012). The transcript is labelled "We heard this", never a pronunciation judgement (FR-011). The recogniser never sees the expected sentence, so it can't paper over mistakes (research R2). Recognition accuracy is measured before release (`eval_voice`, SC-002). Nothing new is generated, so the content-safety filter is unaffected. | Pass |
| III. Learner data privacy | Collected: the learner's voice, only while they're recording, only to produce text for that one attempt (spec Assumptions). Audio stays on the learner's own machine, is decoded in memory and dropped; neither audio nor attempt text is logged or stored (FR-004–FR-006, SC-003). Only the existing mark is kept. Whisper's model weights are downloaded once at install; no learner data is sent anywhere. | Pass |

**Post-design re-check**: Pass. The one change from spec 021 (the attempt
now reaches the learner's own server at reveal) is deliberate and
documented in research R3; it is still never stored, and the page's
privacy label is corrected to "not saved".

## Project Structure

### Documentation (this feature)

```text
specs/022-voice-sentence-recall/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── practice-api.md
│   ├── voice-input.md
│   └── word-diff.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
pyproject.toml                    # restore the `voice` extra (faster-whisper)
src/
├── lib/
│   └── word_diff.py              # NEW: compare(attempt, sentence) -> AttemptComparison | None
├── services/
│   └── speech_client.py          # RESTORED + changed: outcome ok/nothing_heard/unavailable,
│                                 #   English only, VAD, in-memory, preload()
├── tools/
│   └── eval_voice.py             # NEW: word accuracy + timing on recorded clips (SC-002)
└── web/
    ├── app.py                    # POST /api/transcribe; reveal accepts attempt -> comparison;
    │                             #   413 message for recordings; preload at startup
    ├── session_state.py          # can_transcribe(); voice_available in state
    ├── templates/index.html      # Speak button, listening/transcribing notes, label text
    └── static/
        ├── app.js                # recording (restored from spec 009, scoped to sentence recall),
        │                         #   append text, render comparison
        └── style.css             # mic states, missing/extra word styles

tests/
├── fixtures/word_diff_cases.yml  # NEW: reviewed comparison cases (SC-007)
├── unit/
│   ├── test_word_diff.py         # NEW
│   ├── test_speech_client.py     # NEW (faked WhisperModel; not-installed path)
│   ├── test_session_state.py     # + can_transcribe, voice_available
│   ├── test_eval_voice.py        # NEW
│   └── test_web_static_assets.py # + mic wiring, label text, comparison render, 30 s limit
├── contract/
│   └── test_voice_api.py         # NEW: /api/transcribe and reveal+attempt
└── integration/
    └── test_voice_sentence_recall_flow.py  # NEW: select → answer → transcribe → reveal → mark
```

**Structure Decision**: Same single project as specs 001–021. The
comparison is a pure function in `src/lib` (like `us_pronunciation.py`),
the recogniser stays a soft-dependency service in `src/services` (as in
spec 009), and the web layer only wires them in. The CLI is untouched.

## Complexity Tracking

No constitution violations to justify.
