# Test changes for spec 022

Spec 022 brings voice back (only in sentence recall) and sends the
attempt with the reveal, both of which spec 021 tests had pinned as
removed or browser-only. These three existing tests were changed to match
the new, deliberate behaviour (research R3). No other existing test was
changed or removed.

| File | Old test | Now |
|---|---|---|
| `tests/contract/test_practice_api.py` | `test_removed_routes` listed `/api/transcribe` | `/api/transcribe` dropped from the list (it exists again); the other removed routes are still checked for `404` |
| `tests/unit/test_web_static_assets.py` | `test_typed_sentence_attempt_stays_in_the_browser` | rewritten → `test_sentence_attempt_is_sent_only_with_the_reveal` |
| `tests/unit/test_web_static_assets.py` | `test_app_js_example_block` asserted no `/api/transcribe` or `MediaRecorder` anywhere | now asserts they appear only inside the "voice in sentence recall (spec 022)" section |

The session tests planned for `tests/unit/test_session_state.py` (T005)
went into `tests/unit/test_session_example.py`, where the sentence-recall
helpers already live.
