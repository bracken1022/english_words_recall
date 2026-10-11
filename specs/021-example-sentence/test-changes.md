# Test changes for spec 021 (justified deviation)

Spec 021 removes sentence writing and review (the `sentence`/`feedback`
steps, `/api/sentence`, `/api/skip`, `/api/retry-sentence`,
`/api/transcribe`, the correction prompts and voice input). The
constitution's test-first rule normally forbids deleting or weakening
tests. These deletions and rewrites are a justified deviation: they test
behaviour that this feature removes on purpose. Each test is either
**deleted** because it covered only removed behaviour, or **rewritten**
to cover the same guarantee in the example flow (answer → `reveal` →
continue). Tests of unrelated behaviour are unchanged.

## Shared test setup

- **New `tests/conftest.py`**: an autouse fixture makes the local model
  unreachable (`requests.post` raises `ConnectionError`). Examples are
  now made in the background whenever a word comes up, so without this
  any test could reach a real Ollama. Tests that fake the model patch
  `requests.post` themselves, which overrides the fixture.
- **New `tests/fake_examples.py`**: `FakeExampleService`, which stands
  in for `ExampleService` in CLI tests (`no_examples` gives the
  "unavailable" case).
- In the CLI, each word in an example mode now takes two inputs: the
  answer, then Enter to continue. Scripted inputs were changed to match.

## Deleted files (only removed behaviour)

| File | Tests | Why |
|---|---|---|
| `tests/contract/test_ollama_correction_contract.py` | 16 judge/teacher correction tests | `request_correction` and its prompts are removed |
| `tests/integration/test_sentence_correction_flow.py` | 7 CLI sentence-review tests | `run_sentence_step` is removed |
| `tests/unit/test_speech_client.py` | 7 transcription tests | `speech_client.py` and the `voice` extra are removed |

## Rewritten or deleted tests in kept files

### `tests/unit/test_session_state.py`

| Old test | Now |
|---|---|
| `test_submit_answer_advances_to_sentence_step` | rewritten → `test_submit_answer_advances_to_reveal_step` |
| `test_continue_rejected_from_recall_and_sentence` | rewritten → `test_continue_rejected_from_recall` (continue from `reveal` is now valid) |
| `test_current_index_never_decreases_and_ends_in_complete`, `test_continue_from_complete_is_a_no_op`, `test_restart_rejected_when_group_locked` | kept; the `submit_sentence` calls were dropped |
| `test_restart_reloads_vocabulary_and_returns_to_choose`, `test_restart_with_nothing_left_goes_to_empty` | kept; `skip_sentence()` → `continue_to_next()` |
| `test_state_includes_answer_and_correct_for_sentence_step` | rewritten → `test_state_includes_answer_and_correct_for_reveal_step` |
| `test_state_includes_answer_and_correct_for_feedback_step` | deleted (no `feedback` step) |
| `test_skip_sentence_rejected_when_not_in_sentence_step`, `test_skip_sentence_advances_to_recall_for_next_item`, `test_skip_sentence_advances_to_complete_on_last_item` | deleted (`skip_sentence` removed; advancing is covered by the continue tests) |
| `test_skip_sentence_updates_correct_count_from_recall_outcome_only` | rewritten → `test_correct_count_follows_recall_outcomes` |
| `test_skip_sentence_writes_practice_attempt_without_sentence_or_feedback` | rewritten → `test_continue_writes_practice_attempt_without_sentence_or_feedback` |
| `test_concurrent_sentence_submission_is_rejected` | deleted (no sentence submission) |
| `test_init_locked_mode_sentence_mode_sets_flag_false`, `test_select_collection_sentence_mode_sets_flag_false` | renamed → `…_sentence_alias_sets_flag_false` |
| `test_submit_answer_recall_only_correct_skips_sentence_step_and_advances` | renamed → `test_submit_answer_recall_only_correct_waits_in_reveal_and_advances` |
| `test_submit_answer_sentence_mode_unaffected` | rewritten → `test_submit_answer_sentence_alias_behaves_as_example_mode` |
| `test_select_collection_recall_only_then_submit_answer_skips_sentence` | renamed → `…_reveals` |
| `test_sentence_mode_wrong_answer_holds_in_reveal_instead_of_sentence` | rewritten → `test_example_mode_wrong_answer_holds_in_reveal` |
| `test_retry_sentence_returns_from_feedback_to_sentence_for_the_same_word`, `test_retry_sentence_rejected_outside_feedback` | deleted (`retry_sentence` removed) |
| `test_ipa_shown_on_sentence_and_feedback` | rewritten → `test_ipa_shown_on_reveal_in_example_mode` |
| `test_pos_shown_on_sentence_and_feedback` | rewritten → `test_pos_shown_on_reveal_in_example_mode` |
| Recall-only tests patched with `request_correction` | kept; the patch and `assert_not_called` were dropped |

### `tests/contract/test_web_api_contract.py`

| Old test | Now |
|---|---|
| `test_post_continue_rejected_from_sentence` | deleted (continue from `reveal` is valid) |
| `test_post_sentence_*` (6 tests), `test_post_sentence_rejects_second_request_while_one_in_progress` | deleted (`/api/sentence` removed; `test_practice_api.py::test_removed_routes` checks for a 404) |
| `test_get_state_sentence_step_includes_answer_and_correct` | rewritten → `test_get_state_reveal_step_includes_answer_and_correct` |
| `test_get_state_feedback_step_includes_answer_and_correct` | deleted |
| `test_get_state_reports_voice_available_*`, `test_voice_available_present_on_every_step_not_just_sentence` | deleted (`voice_available` removed) |
| `test_post_transcribe_*` (3 tests) | deleted (`/api/transcribe` removed) |
| `test_post_skip_*` (3 tests) | deleted (`/api/skip` removed) |
| `test_post_retry_sentence_*` (2 tests) | deleted (`/api/retry-sentence` removed) |
| complete/restart tests | kept; `/api/skip` → `/api/continue` |
| `test_post_select_recall_only_then_answer_skips_sentence_step` | rewritten → `…_reveals_without_example` (asserts `example_status == "off"`) |
| `test_post_select_mode_absent_defaults_to_sentence`, `…_invalid_mode_defaults_to_sentence` | rewritten → `…_defaults_to_example` |

### `tests/integration/test_web_session_flow.py`

| Old test | Now |
|---|---|
| `test_recall_only_cycle_hides_english_until_submitted` | kept; the expected step is now `reveal` |
| `test_full_recall_sentence_feedback_cycle_writes_progress_log` | rewritten → `test_full_recall_example_cycle_writes_progress_log` |
| `test_skipped_word_counts_correctly_and_is_distinguishable_in_history` | rewritten → `test_every_word_counts_toward_the_tally` |
| `test_full_choose_practice_complete_restart_loop` | kept; `/api/skip` → `/api/continue` |
| `test_full_record_transcribe_review_submit_flow` | deleted (voice input removed) |
| `test_word_feedback_and_sentence_prompt_both_present_after_submission` | rewritten → `test_word_feedback_and_example_both_present_after_submission` |
| `test_word_feedback_survives_a_simulated_reload_mid_sentence_step` | rewritten → `…_at_reveal` |

### Smaller files

| File | Change |
|---|---|
| `tests/integration/test_multi_account_flow.py` | `test_sentence_review_belongs_only_to_its_account` → `test_example_belongs_only_to_its_account`; `test_logout_mid_sentence_…` → `test_logout_mid_reveal_…`; mode `sentence` → `example`, step `sentence` → `reveal` |
| `tests/integration/test_session_mode.py` | `test_recall_only_mode_never_requests_correction` → `test_recall_only_mode_never_asks_for_examples`; `test_sentence_mode_default_still_requests_correction_per_word` → `test_example_mode_default_shows_an_example_per_word`; added `test_sentence_mode_means_example_mode` and `test_no_example_available_still_completes` |
| `tests/integration/test_session_order.py` | kept; the correction mock became `FakeExampleService`, and the inputs became answer + Enter |
| `tests/integration/test_non_interactive_output.py` | kept; the fallback message is now "Writing an example..." and the output shows the example instead of review feedback |
| `tests/integration/test_determinism.py` | the two LLM-verdict tests became `test_grading_and_order_identical_with_or_without_examples` |
| `tests/integration/test_progress_log_readability.py` | kept; asserts that no `sentence:`/`feedback:` lines are written |
| `tests/integration/test_session_group_filter.py` | kept; uses `FakeExampleService` and answer + Enter inputs |
| `tests/integration/test_edge_cases.py` | `test_extremely_long_sentence_does_not_crash` → `test_extremely_long_answer_does_not_crash` |
| `tests/integration/test_ipa_flow.py` | `test_sentence_prompt_shows_ipa` and `test_run_session_passes_ipa_to_sentence_step` deleted; added `test_cli_pronunciation_comes_before_the_example` |
| `tests/integration/test_word_lists_flow.py`, `tests/unit/test_session_registry.py` | mode `sentence` → `example` (same behaviour, current name) |
| `tests/unit/test_session_remove.py` | `test_remove_at_sentence_logs_like_skip` → `test_remove_at_example_reveal_logs_the_attempt`; `test_wrong_step_feedback` deleted |
| `tests/contract/test_web_auth_contract.py` | the guarded-route list drops the removed routes and adds `/api/example/new` and `/api/sentence-recall` |
| `tests/unit/test_web_static_assets.py` | sections checked are now `recall-view` only; stamp wording drops "Natural"/"Small fix"; `test_answer_and_sentence_forms_use_field_row` → `test_answer_form_uses_field_row`; `test_check_and_review_buttons_disable_when_empty` → `test_check_button_disables_when_empty`; session controls are now End session + New example; IPA/pos render checks name `renderRecallResult`; deleted `test_app_js_confirms_before_skipping_an_empty_sentence`, `test_app_js_wires_up_voice_input`, `test_spinner_uses_hidden_attribute_not_a_separate_mechanism` (the spinner only covered review) and `test_sentence_view_has_target_ipa`. The `[hidden]` override test is kept. |
| `tests/unit/test_models_practice_attempt.py`, `tests/contract/test_progress_log_contract.py` | additions only (`sentence_recall` mark; old logs with sentence/feedback still load) |
| `tests/unit/test_design_workflow_skill.py` | unchanged; it checks the design skill's text, not the app |
