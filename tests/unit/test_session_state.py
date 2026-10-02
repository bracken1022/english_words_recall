from pathlib import Path
from unittest.mock import patch

import pytest

from src.services.llm_client import CorrectionResult
from src.web.session_state import UNGROUPED_KEY, PracticeSession, WrongStepError


def _write_vocab(tmp_path: Path) -> Path:
    vocab_dir = tmp_path / "vocab"
    vocab_dir.mkdir()
    (vocab_dir / "unit1.md").write_text(
        "---\nenglish: receive\nchinese: 收到\n---\n\n---\nenglish: give up\nchinese: 放弃\n---\n"
    )
    return vocab_dir


def _write_multi_group_vocab(tmp_path: Path) -> Path:
    vocab_dir = tmp_path / "vocab"
    vocab_dir.mkdir()
    (vocab_dir / "words.md").write_text(
        "---\nenglish: receive\nchinese: 收到\ngroup: unit1\n---\n\n"
        "---\nenglish: tailor\nchinese: 裁缝\ngroup: t-words\n---\n\n"
        "---\nenglish: mystery\nchinese: 谜\n---\n"
    )
    return vocab_dir


def test_empty_pool_starts_in_empty_step(tmp_path: Path):
    vocab_dir = tmp_path / "empty_vocab"
    vocab_dir.mkdir()
    session = PracticeSession(vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md")
    assert session.step == "empty"
    assert session.items == []


def test_non_empty_pool_starts_in_recall_step_at_index_zero(tmp_path: Path):
    vocab_dir = _write_vocab(tmp_path)
    session = PracticeSession(vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md")
    assert session.step == "recall"
    assert session.current_index == 0
    assert len(session.items) == 2


def test_submit_answer_advances_to_sentence_step(tmp_path: Path):
    vocab_dir = _write_vocab(tmp_path)
    session = PracticeSession(vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md")
    result = session.submit_answer("receive")
    assert result["correct"] is True
    assert session.step == "sentence"


def test_submit_answer_rejected_when_not_in_recall_step(tmp_path: Path):
    vocab_dir = _write_vocab(tmp_path)
    session = PracticeSession(vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md")
    session.submit_answer("receive")
    with pytest.raises(WrongStepError):
        session.submit_answer("receive")


def test_continue_rejected_from_recall_and_sentence(tmp_path: Path):
    vocab_dir = _write_vocab(tmp_path)
    session = PracticeSession(vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md")
    with pytest.raises(WrongStepError):
        session.continue_to_next()
    session.submit_answer("receive")
    with pytest.raises(WrongStepError):
        session.continue_to_next()


def test_current_index_never_decreases_and_ends_in_complete(tmp_path: Path):
    vocab_dir = _write_vocab(tmp_path)
    session = PracticeSession(vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md")

    session.submit_answer("receive")
    session.submit_sentence("I received a gift.", base_url="x", model="m", correction_fn=lambda *a, **k: _stub())
    assert session.current_index == 0
    session.continue_to_next()
    assert session.current_index == 1
    assert session.step == "recall"

    session.submit_answer("give up")
    session.submit_sentence("I gave up.", base_url="x", model="m", correction_fn=lambda *a, **k: _stub())
    session.continue_to_next()
    assert session.current_index == 2
    assert session.step == "complete"


def test_continue_from_complete_is_a_no_op(tmp_path: Path):
    vocab_dir = tmp_path / "one_item"
    vocab_dir.mkdir()
    (vocab_dir / "unit1.md").write_text("---\nenglish: receive\nchinese: 收到\n---\n")
    session = PracticeSession(vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md")
    session.submit_answer("receive")
    session.submit_sentence("I received a gift.", base_url="x", model="m", correction_fn=lambda *a, **k: _stub())
    session.continue_to_next()
    assert session.step == "complete"
    session.continue_to_next()  # no-op, must not raise
    assert session.step == "complete"


def _stub():
    from src.services.llm_client import CorrectionResult

    return CorrectionResult(
        available=True, uses_expression=True, needs_correction=False, corrected=None, explanation=None
    )


def test_state_omits_answer_and_correct_for_recall_empty_complete(tmp_path: Path):
    vocab_dir = _write_vocab(tmp_path)
    session = PracticeSession(vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md")
    assert "answer" not in session.state()
    assert "correct" not in session.state()

    empty_dir = tmp_path / "empty_vocab"
    empty_dir.mkdir()
    empty_session = PracticeSession(vocab_dir=empty_dir, progress_file=tmp_path / "p2.md")
    assert "answer" not in empty_session.state()
    assert "correct" not in empty_session.state()


def test_state_includes_answer_and_correct_for_sentence_step(tmp_path: Path):
    vocab_dir = _write_vocab(tmp_path)
    session = PracticeSession(vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md")
    session.submit_answer("receive")
    state = session.state()
    assert state["step"] == "sentence"
    assert state["answer"] == "receive"
    assert state["correct"] is True


def test_state_includes_answer_and_correct_for_feedback_step(tmp_path: Path):
    vocab_dir = _write_vocab(tmp_path)
    session = PracticeSession(vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md")
    session.submit_answer("receive")
    session.submit_sentence("I received a gift.", base_url="x", model="m", correction_fn=lambda *a, **k: _stub())
    state = session.state()
    assert state["step"] == "feedback"
    assert state["answer"] == "receive"
    assert state["correct"] is True


def test_skip_sentence_rejected_when_not_in_sentence_step(tmp_path: Path):
    vocab_dir = _write_vocab(tmp_path)
    session = PracticeSession(vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md")
    with pytest.raises(WrongStepError):
        session.skip_sentence()  # still in "recall"

    session.submit_answer("receive")
    session.submit_sentence("I received a gift.", base_url="x", model="m", correction_fn=lambda *a, **k: _stub())
    assert session.step == "feedback"
    with pytest.raises(WrongStepError):
        session.skip_sentence()  # now in "feedback", not "sentence"


def test_skip_sentence_advances_to_recall_for_next_item(tmp_path: Path):
    vocab_dir = _write_vocab(tmp_path)
    session = PracticeSession(vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md")
    session.submit_answer("receive")
    assert session.step == "sentence"

    session.skip_sentence()
    assert session.step == "recall"
    assert session.current_index == 1
    assert session.pending_attempt is None


def test_skip_sentence_advances_to_complete_on_last_item(tmp_path: Path):
    vocab_dir = tmp_path / "one_item"
    vocab_dir.mkdir()
    (vocab_dir / "unit1.md").write_text("---\nenglish: receive\nchinese: 收到\n---\n")
    session = PracticeSession(vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md")
    session.submit_answer("receive")

    session.skip_sentence()
    assert session.step == "complete"


def test_skip_sentence_updates_correct_count_from_recall_outcome_only(tmp_path: Path):
    vocab_dir = _write_vocab(tmp_path)
    session = PracticeSession(vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md")

    session.submit_answer("receive")  # correct
    session.skip_sentence()
    assert session.correct_count == 1

    session.submit_answer("wrong")  # incorrect: held in "reveal", no sentence step
    session.continue_to_next()
    assert session.correct_count == 1  # unchanged
    assert session.step == "complete"
    state = session.state()
    assert state["total"] == 2
    assert state["correct"] == 1


def test_skip_sentence_writes_practice_attempt_without_sentence_or_feedback(tmp_path: Path):
    vocab_dir = _write_vocab(tmp_path)
    progress_file = tmp_path / "progress.md"
    session = PracticeSession(vocab_dir=vocab_dir, progress_file=progress_file)

    session.submit_answer("receive")
    session.skip_sentence()

    progress_text = progress_file.read_text(encoding="utf-8")
    assert "item: receive" in progress_text
    assert "answer: receive" in progress_text
    assert "correct: true" in progress_text
    assert "sentence:" not in progress_text
    assert "feedback:" not in progress_text


def test_default_behavior_unchanged_when_offer_choice_omitted(tmp_path: Path):
    """Every existing caller that doesn't know about the collection-choice
    feature (offer_choice omitted) must keep exactly today's behavior,
    regardless of whether group is also given."""
    vocab_dir = _write_vocab(tmp_path)
    session = PracticeSession(vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md")
    assert session.step == "recall"
    assert session.group_locked is True


def test_offer_choice_starts_in_choose_step_when_group_not_given(tmp_path: Path):
    vocab_dir = _write_multi_group_vocab(tmp_path)
    session = PracticeSession(
        vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md", offer_choice=True
    )
    assert session.step == "choose"
    assert session.group_locked is False
    assert len(session.all_items) == 3
    assert session.items == []


def test_offer_choice_with_empty_pool_still_starts_empty(tmp_path: Path):
    vocab_dir = tmp_path / "empty_vocab"
    vocab_dir.mkdir()
    session = PracticeSession(
        vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md", offer_choice=True
    )
    assert session.step == "empty"
    assert session.group_locked is False


def test_offer_choice_ignored_when_group_is_given(tmp_path: Path):
    """A pre-selected group at startup always wins: no "choose" step, even
    if offer_choice=True is also passed (group_locked stays True)."""
    vocab_dir = _write_multi_group_vocab(tmp_path)
    session = PracticeSession(
        vocab_dir=vocab_dir,
        progress_file=tmp_path / "progress.md",
        group="unit1",
        offer_choice=True,
    )
    assert session.step == "recall"
    assert session.group_locked is True
    assert len(session.items) == 1


def test_available_collections_ordering_and_counts(tmp_path: Path):
    vocab_dir = _write_multi_group_vocab(tmp_path)
    session = PracticeSession(
        vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md", offer_choice=True
    )
    assert session._available_collections() == [
        {"key": None, "label": "Practice everything", "count": 3},
        {"key": "t-words", "label": "t-words", "count": 1},
        {"key": "unit1", "label": "unit1", "count": 1},
        {"key": "__ungrouped__", "label": "Ungrouped words", "count": 1},
    ]


def test_available_collections_omits_ungrouped_entry_when_none_exist(tmp_path: Path):
    vocab_dir = tmp_path / "vocab"
    vocab_dir.mkdir()
    (vocab_dir / "words.md").write_text("---\nenglish: receive\nchinese: 收到\ngroup: unit1\n---\n")
    session = PracticeSession(
        vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md", offer_choice=True
    )
    assert session._available_collections() == [
        {"key": None, "label": "Practice everything", "count": 1},
        {"key": "unit1", "label": "unit1", "count": 1},
    ]


def test_state_choose_step_includes_collections(tmp_path: Path):
    vocab_dir = _write_multi_group_vocab(tmp_path)
    session = PracticeSession(
        vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md", offer_choice=True
    )
    state = session.state()
    assert state["step"] == "choose"
    assert state["collections"][0] == {"key": None, "label": "Practice everything", "count": 3}
    assert state["warnings"] == []


def test_select_collection_rejected_when_not_in_choose_step(tmp_path: Path):
    vocab_dir = _write_vocab(tmp_path)
    session = PracticeSession(vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md")
    assert session.step == "recall"  # offer_choice not passed, never "choose"
    with pytest.raises(WrongStepError):
        session.select_collection(None)


def test_select_collection_named_group_filters_and_resets_progress(tmp_path: Path):
    vocab_dir = _write_multi_group_vocab(tmp_path)
    session = PracticeSession(
        vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md", offer_choice=True
    )
    session.select_collection("unit1")
    assert session.step == "recall"
    assert [i.english for i in session.items] == ["receive"]
    assert session.current_index == 0
    assert session.pending_attempt is None
    assert session.correct_count == 0


def test_select_collection_none_means_practice_everything(tmp_path: Path):
    vocab_dir = _write_multi_group_vocab(tmp_path)
    session = PracticeSession(
        vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md", offer_choice=True
    )
    session.select_collection(None)
    assert session.step == "recall"
    assert len(session.items) == 3


def test_select_collection_ungrouped_key_selects_untagged_items(tmp_path: Path):
    vocab_dir = _write_multi_group_vocab(tmp_path)
    session = PracticeSession(
        vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md", offer_choice=True
    )
    session.select_collection(UNGROUPED_KEY)
    assert session.step == "recall"
    assert [i.english for i in session.items] == ["mystery"]


def test_select_collection_preserves_original_item_order(tmp_path: Path):
    vocab_dir = _write_vocab(tmp_path)  # "receive" then "give up", both ungrouped
    session = PracticeSession(
        vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md", offer_choice=True
    )
    session.select_collection(UNGROUPED_KEY)
    assert [i.english for i in session.items] == ["receive", "give up"]


def test_restart_rejected_when_not_complete(tmp_path: Path):
    vocab_dir = _write_multi_group_vocab(tmp_path)
    session = PracticeSession(
        vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md", offer_choice=True
    )
    with pytest.raises(WrongStepError):
        session.restart()  # still "choose"


def test_restart_rejected_when_group_locked(tmp_path: Path):
    vocab_dir = _write_vocab(tmp_path)
    session = PracticeSession(vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md")
    session.submit_answer("receive")
    session.submit_sentence("I received a gift.", base_url="x", model="m", correction_fn=lambda *a, **k: _stub())
    session.continue_to_next()
    session.submit_answer("give up")
    session.submit_sentence("I gave up.", base_url="x", model="m", correction_fn=lambda *a, **k: _stub())
    session.continue_to_next()
    assert session.step == "complete"
    assert session.group_locked is True
    with pytest.raises(WrongStepError):
        session.restart()


def test_restart_reloads_vocabulary_and_returns_to_choose(tmp_path: Path):
    vocab_dir = _write_multi_group_vocab(tmp_path)
    session = PracticeSession(
        vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md", offer_choice=True
    )
    session.select_collection(UNGROUPED_KEY)
    session.submit_answer("mystery")
    session.skip_sentence()
    assert session.step == "complete"

    (vocab_dir / "more.md").write_text("---\nenglish: tablet\nchinese: 平板\ngroup: unit1\n---\n")
    session.restart()

    assert session.step == "choose"
    assert len(session.all_items) == 4
    assert any(item.english == "tablet" for item in session.all_items)


def test_restart_with_nothing_left_goes_to_empty(tmp_path: Path):
    vocab_dir = tmp_path / "vocab"
    vocab_dir.mkdir()
    (vocab_dir / "one.md").write_text("---\nenglish: receive\nchinese: 收到\n---\n")
    session = PracticeSession(
        vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md", offer_choice=True
    )
    session.select_collection(None)
    session.submit_answer("receive")
    session.skip_sentence()
    assert session.step == "complete"

    (vocab_dir / "one.md").unlink()
    session.restart()
    assert session.step == "empty"


def test_concurrent_sentence_submission_is_rejected(tmp_path: Path):
    """Simulates 'a second request arrives while the first is still
    running' deterministically: correction_fn re-enters submit_sentence on
    the same session before returning (research.md)."""
    vocab_dir = _write_vocab(tmp_path)
    session = PracticeSession(vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md")
    session.submit_answer("receive")

    inner_raised = {}

    def reentrant_correction(*args, **kwargs):
        try:
            session.submit_sentence("a second sentence", base_url="x", model="m")
        except WrongStepError as exc:
            inner_raised["error"] = exc
        return _stub()

    session.submit_sentence("I received a gift.", base_url="x", model="m", correction_fn=reentrant_correction)

    assert "error" in inner_raised
    assert session.step == "feedback"  # the original (outer) call still completed normally


@patch("src.web.session_state.random.shuffle")
def test_init_locked_mode_random_order_shuffles_once(mock_shuffle, tmp_path: Path):
    vocab_dir = _write_vocab(tmp_path)
    session = PracticeSession(
        vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md", order="random"
    )
    mock_shuffle.assert_called_once_with(session.items)


@patch("src.web.session_state.random.shuffle")
def test_init_locked_mode_sequential_order_never_shuffles(mock_shuffle, tmp_path: Path):
    vocab_dir = _write_vocab(tmp_path)
    PracticeSession(vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md", order="sequential")
    mock_shuffle.assert_not_called()


@patch("src.web.session_state.random.shuffle")
def test_init_locked_mode_default_order_never_shuffles(mock_shuffle, tmp_path: Path):
    vocab_dir = _write_vocab(tmp_path)
    PracticeSession(vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md")
    mock_shuffle.assert_not_called()


def test_init_random_order_is_a_permutation_of_the_same_items(tmp_path: Path):
    vocab_dir = _write_vocab(tmp_path)
    session = PracticeSession(
        vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md", order="random"
    )
    assert sorted(i.english for i in session.items) == ["give up", "receive"]


@patch("src.web.session_state.random.shuffle")
def test_select_collection_random_order_shuffles_once(mock_shuffle, tmp_path: Path):
    vocab_dir = _write_multi_group_vocab(tmp_path)
    session = PracticeSession(
        vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md", offer_choice=True
    )
    session.select_collection(None, order="random")
    mock_shuffle.assert_called_once_with(session.items)


@patch("src.web.session_state.random.shuffle")
def test_select_collection_sequential_order_never_shuffles(mock_shuffle, tmp_path: Path):
    vocab_dir = _write_multi_group_vocab(tmp_path)
    session = PracticeSession(
        vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md", offer_choice=True
    )
    session.select_collection(None, order="sequential")
    mock_shuffle.assert_not_called()


@patch("src.web.session_state.random.shuffle")
def test_select_collection_default_order_never_shuffles(mock_shuffle, tmp_path: Path):
    vocab_dir = _write_multi_group_vocab(tmp_path)
    session = PracticeSession(
        vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md", offer_choice=True
    )
    session.select_collection(None)
    mock_shuffle.assert_not_called()


def test_select_collection_random_order_is_a_permutation_of_the_same_items(tmp_path: Path):
    vocab_dir = _write_multi_group_vocab(tmp_path)
    session = PracticeSession(
        vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md", offer_choice=True
    )
    session.select_collection(None, order="random")
    assert sorted(i.english for i in session.items) == ["mystery", "receive", "tailor"]


def test_init_locked_mode_recall_only_sets_flag_true(tmp_path: Path):
    vocab_dir = _write_vocab(tmp_path)
    session = PracticeSession(
        vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md", mode="recall-only"
    )
    assert session.recall_only is True


def test_init_locked_mode_sentence_mode_sets_flag_false(tmp_path: Path):
    vocab_dir = _write_vocab(tmp_path)
    session = PracticeSession(
        vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md", mode="sentence"
    )
    assert session.recall_only is False


def test_init_locked_mode_default_sets_flag_false(tmp_path: Path):
    vocab_dir = _write_vocab(tmp_path)
    session = PracticeSession(vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md")
    assert session.recall_only is False


def test_init_interactive_placeholder_flag_is_false_before_selection(tmp_path: Path):
    vocab_dir = _write_multi_group_vocab(tmp_path)
    session = PracticeSession(
        vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md", offer_choice=True
    )
    assert session.recall_only is False


def test_select_collection_recall_only_sets_flag_true(tmp_path: Path):
    vocab_dir = _write_multi_group_vocab(tmp_path)
    session = PracticeSession(
        vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md", offer_choice=True
    )
    session.select_collection(None, mode="recall-only")
    assert session.recall_only is True


def test_select_collection_sentence_mode_sets_flag_false(tmp_path: Path):
    vocab_dir = _write_multi_group_vocab(tmp_path)
    session = PracticeSession(
        vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md", offer_choice=True
    )
    session.select_collection(None, mode="sentence")
    assert session.recall_only is False


def test_select_collection_default_mode_sets_flag_false(tmp_path: Path):
    vocab_dir = _write_multi_group_vocab(tmp_path)
    session = PracticeSession(
        vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md", offer_choice=True
    )
    session.select_collection(None)
    assert session.recall_only is False


@patch("src.web.session_state.request_correction")
def test_submit_answer_recall_only_correct_skips_sentence_step_and_advances(mock_request, tmp_path: Path):
    """A correct recall-only answer never visits "sentence" (spec 012).
    Since the Broadsheet redesign it waits in "reveal" for the learner,
    then finalizes and advances on continue."""
    vocab_dir = _write_vocab(tmp_path)  # "receive" then "give up"
    progress_file = tmp_path / "progress.md"
    session = PracticeSession(vocab_dir=vocab_dir, progress_file=progress_file, mode="recall-only")

    result = session.submit_answer("receive")
    assert result["correct"] is True
    assert session.step == "reveal"
    session.continue_to_next()
    assert session.step == "recall"
    assert session.current_index == 1
    assert session.correct_count == 1
    assert session.pending_attempt is None
    mock_request.assert_not_called()


@patch("src.web.session_state.request_correction")
def test_submit_answer_recall_only_incorrect_holds_in_reveal_step(mock_request, tmp_path: Path):
    """Spec 013: a wrong recall-only answer must NOT auto-advance — it
    stops in "reveal", holding the attempt unfinalized until
    continue_to_next() is called."""
    vocab_dir = _write_vocab(tmp_path)  # "receive" then "give up"
    progress_file = tmp_path / "progress.md"
    session = PracticeSession(vocab_dir=vocab_dir, progress_file=progress_file, mode="recall-only")

    result = session.submit_answer("wrong")
    assert result["correct"] is False
    assert session.step == "reveal"
    assert session.current_index == 0
    assert session.correct_count == 0
    assert session.pending_attempt is not None
    mock_request.assert_not_called()

    progress_text = progress_file.read_text(encoding="utf-8") if progress_file.exists() else ""
    assert "item: receive" not in progress_text


@patch("src.web.session_state.request_correction")
def test_continue_to_next_from_reveal_records_attempt_and_advances(mock_request, tmp_path: Path):
    vocab_dir = _write_vocab(tmp_path)  # "receive" then "give up"
    progress_file = tmp_path / "progress.md"
    session = PracticeSession(vocab_dir=vocab_dir, progress_file=progress_file, mode="recall-only")

    session.submit_answer("wrong")
    assert session.step == "reveal"

    session.continue_to_next()

    assert session.step == "recall"
    assert session.current_index == 1
    assert session.correct_count == 0
    assert session.pending_attempt is None
    mock_request.assert_not_called()

    progress_text = progress_file.read_text(encoding="utf-8")
    assert "item: receive" in progress_text
    assert "answer: wrong" in progress_text
    assert "correct: false" in progress_text
    assert "sentence:" not in progress_text
    assert "feedback:" not in progress_text


@patch("src.web.session_state.request_correction")
def test_continue_to_next_from_reveal_on_last_item_reaches_complete(mock_request, tmp_path: Path):
    vocab_dir = tmp_path / "one_item"
    vocab_dir.mkdir()
    (vocab_dir / "unit1.md").write_text("---\nenglish: receive\nchinese: 收到\n---\n")
    session = PracticeSession(
        vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md", mode="recall-only"
    )

    session.submit_answer("wrong")
    session.continue_to_next()

    assert session.step == "complete"
    state = session.state()
    assert state["total"] == 1
    assert state["correct"] == 0


def test_state_reveal_step_exposes_answer_fields_without_sentence_or_feedback(tmp_path: Path):
    vocab_dir = _write_vocab(tmp_path)
    session = PracticeSession(vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md", mode="recall-only")

    session.submit_answer("wrong")
    state = session.state()

    assert state["step"] == "reveal"
    assert state["answer"] == "wrong"
    assert state["correct"] is False
    assert state["accepted_expressions"] == ["receive"]
    assert "sentence" not in state
    assert "feedback" not in state


@patch("src.web.session_state.request_correction")
def test_submit_answer_recall_only_writes_progress_without_sentence_or_feedback(
    mock_request, tmp_path: Path
):
    vocab_dir = _write_vocab(tmp_path)
    progress_file = tmp_path / "progress.md"
    session = PracticeSession(vocab_dir=vocab_dir, progress_file=progress_file, mode="recall-only")

    session.submit_answer("receive")
    session.continue_to_next()

    text = progress_file.read_text(encoding="utf-8")
    assert "item: receive" in text
    assert "answer: receive" in text
    assert "correct: true" in text
    assert "sentence:" not in text
    assert "feedback:" not in text
    mock_request.assert_not_called()


def test_submit_answer_sentence_mode_unaffected(tmp_path: Path):
    vocab_dir = _write_vocab(tmp_path)
    session = PracticeSession(vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md", mode="sentence")
    result = session.submit_answer("receive")
    assert result["correct"] is True
    assert session.step == "sentence"
    assert session.pending_attempt is not None


@patch("src.web.session_state.request_correction")
def test_select_collection_recall_only_then_submit_answer_skips_sentence(mock_request, tmp_path: Path):
    vocab_dir = _write_multi_group_vocab(tmp_path)  # unit1 -> only "receive"
    session = PracticeSession(
        vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md", offer_choice=True
    )
    session.select_collection("unit1", mode="recall-only")
    assert session.recall_only is True

    session.submit_answer("receive")
    assert session.step == "reveal"
    session.continue_to_next()
    assert session.step == "complete"
    mock_request.assert_not_called()



# --- Broadsheet redesign: handoff recall flow, end session, retry sentence ---


def test_sentence_mode_wrong_answer_holds_in_reveal_instead_of_sentence(tmp_path: Path):
    """Handoff flow: only a correct recall earns the sentence step; a wrong
    answer in sentence mode stops in "reveal" like recall-only does."""
    vocab_dir = _write_vocab(tmp_path)
    progress_file = tmp_path / "progress.md"
    session = PracticeSession(vocab_dir=vocab_dir, progress_file=progress_file, mode="sentence")

    result = session.submit_answer("wrong")

    assert result["correct"] is False
    assert session.step == "reveal"
    assert not progress_file.exists()

    session.continue_to_next()
    assert session.step == "recall"
    assert session.current_index == 1
    text = progress_file.read_text(encoding="utf-8")
    assert "answer: wrong" in text
    assert "sentence:" not in text


@patch("src.web.session_state.request_correction")
def test_recall_only_correct_answer_waits_in_reveal_until_continue(mock_request, tmp_path: Path):
    """Handoff flow: a correct recall-only answer shows its result and
    waits for the learner instead of auto-advancing."""
    vocab_dir = _write_vocab(tmp_path)
    progress_file = tmp_path / "progress.md"
    session = PracticeSession(vocab_dir=vocab_dir, progress_file=progress_file, mode="recall-only")

    session.submit_answer("receive")
    assert session.step == "reveal"
    assert session.correct_count == 0
    assert session.state()["correct"] is True

    session.continue_to_next()
    assert session.step == "recall"
    assert session.correct_count == 1
    assert "correct: true" in progress_file.read_text(encoding="utf-8")
    mock_request.assert_not_called()


def test_state_reports_position_and_total_during_a_word(tmp_path: Path):
    vocab_dir = _write_vocab(tmp_path)
    session = PracticeSession(vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md")

    state = session.state()
    assert state["position"] == 1
    assert state["total"] == 2

    session.submit_answer("wrong")
    session.continue_to_next()
    assert session.state()["position"] == 2


def test_state_can_end_session_only_when_not_group_locked(tmp_path: Path):
    vocab_dir = _write_multi_group_vocab(tmp_path)
    interactive = PracticeSession(
        vocab_dir=vocab_dir, progress_file=tmp_path / "p1.md", offer_choice=True
    )
    interactive.select_collection("unit1")
    assert interactive.state()["can_end_session"] is True

    locked = PracticeSession(vocab_dir=vocab_dir, progress_file=tmp_path / "p2.md", group="unit1")
    assert locked.state()["can_end_session"] is False


def test_end_session_mid_word_returns_to_choose_without_logging(tmp_path: Path):
    vocab_dir = _write_multi_group_vocab(tmp_path)
    progress_file = tmp_path / "progress.md"
    session = PracticeSession(vocab_dir=vocab_dir, progress_file=progress_file, offer_choice=True)
    session.select_collection(None)
    session.submit_answer("wrong")
    assert session.step == "reveal"

    session.end_session()

    assert session.step == "choose"
    assert session.pending_attempt is None
    assert not progress_file.exists()


def test_end_session_rejected_when_group_locked_or_not_in_a_word(tmp_path: Path):
    vocab_dir = _write_multi_group_vocab(tmp_path)
    locked = PracticeSession(vocab_dir=vocab_dir, progress_file=tmp_path / "p1.md", group="unit1")
    with pytest.raises(WrongStepError):
        locked.end_session()

    choosing = PracticeSession(
        vocab_dir=vocab_dir, progress_file=tmp_path / "p2.md", offer_choice=True
    )
    with pytest.raises(WrongStepError):
        choosing.end_session()


def test_retry_sentence_returns_from_feedback_to_sentence_for_the_same_word(tmp_path: Path):
    vocab_dir = _write_vocab(tmp_path)
    progress_file = tmp_path / "progress.md"
    session = PracticeSession(vocab_dir=vocab_dir, progress_file=progress_file)
    session.submit_answer("receive")
    fake = lambda *a, **k: CorrectionResult(
        available=True, uses_expression=True, needs_correction=False, corrected="", explanation=""
    )
    session.submit_sentence("I receive mail.", base_url="x", model="y", correction_fn=fake)
    assert session.step == "feedback"

    session.retry_sentence()

    assert session.step == "sentence"
    assert session.current_index == 0
    assert "sentence" not in session.pending_attempt
    assert "feedback" not in session.state()

    session.submit_sentence("I received it.", base_url="x", model="y", correction_fn=fake)
    session.continue_to_next()
    assert session.correct_count == 1
    text = progress_file.read_text(encoding="utf-8")
    assert "sentence: I receive mail." in text
    assert "sentence: I received it." in text


def test_retry_sentence_rejected_outside_feedback(tmp_path: Path):
    vocab_dir = _write_vocab(tmp_path)
    session = PracticeSession(vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md")
    with pytest.raises(WrongStepError):
        session.retry_sentence()


# --- spec 016: set_vocab_dir -------------------------------------------------


def _vocab_at(path: Path, text: str) -> Path:
    path.mkdir(parents=True)
    (path / "words.md").write_text(text, encoding="utf-8")
    return path


def test_set_vocab_dir_reloads_on_choose(tmp_path: Path):
    a = _write_vocab(tmp_path)
    b = _vocab_at(tmp_path / "b", "---\nenglish: tailor\nchinese: 裁缝\ngroup: mine\n---\n")
    session = PracticeSession(vocab_dir=a, progress_file=tmp_path / "p.md", offer_choice=True)
    session.set_vocab_dir(b)
    assert session.vocab_dir == b
    assert [i.english for i in session.all_items] == ["tailor"]
    assert session.step == "choose"


def test_set_vocab_dir_moves_empty_to_choose_and_back(tmp_path: Path):
    empty = tmp_path / "empty"
    empty.mkdir()
    b = _vocab_at(tmp_path / "b", "---\nenglish: tailor\nchinese: 裁缝\n---\n")
    session = PracticeSession(vocab_dir=empty, progress_file=tmp_path / "p.md", offer_choice=True)
    assert session.step == "empty"
    session.set_vocab_dir(b)
    assert session.step == "choose"
    session.set_vocab_dir(empty)
    assert session.step == "empty"


def test_set_vocab_dir_mid_session_only_stores_path(tmp_path: Path):
    a = _write_vocab(tmp_path)
    b = _vocab_at(tmp_path / "b", "---\nenglish: tailor\nchinese: 裁缝\n---\n")
    session = PracticeSession(vocab_dir=a, progress_file=tmp_path / "p.md", offer_choice=True)
    session.select_collection(None)
    before = (list(session.items), session.step, session.current_index, list(session.all_items))
    session.set_vocab_dir(b)
    assert (session.items, session.step, session.current_index, session.all_items) == before
    session.end_session()
    assert [i.english for i in session.all_items] == ["tailor"]


def test_set_vocab_dir_group_locked_only_stores_path(tmp_path: Path):
    a = _write_multi_group_vocab(tmp_path)
    b = _vocab_at(tmp_path / "b", "---\nenglish: tailor\nchinese: 裁缝\n---\n")
    session = PracticeSession(vocab_dir=a, progress_file=tmp_path / "p.md", group="unit1")
    before = (list(session.items), session.step)
    session.set_vocab_dir(b)
    assert session.vocab_dir == b
    assert (session.items, session.step) == before


# --- spec 017: ipa exposed only after recall ----------------------------------


def _ipa_vocab(tmp_path: Path) -> Path:
    vocab_dir = tmp_path / "ipa-vocab"
    vocab_dir.mkdir()
    (vocab_dir / "unit1.md").write_text(
        "---\nenglish: receive\nipa: rɪˈsiːv\nchinese: 收到\n---\n\n"
        "---\nenglish: give up\nchinese: 放弃\n---\n",
        encoding="utf-8",
    )
    return vocab_dir


def test_ipa_hidden_during_recall(tmp_path: Path):
    session = PracticeSession(vocab_dir=_ipa_vocab(tmp_path), progress_file=tmp_path / "p.md")
    assert session.step == "recall"
    assert "ipa" not in session.state()
    assert "rɪˈsiːv" not in str(session.state())


@patch("src.web.session_state.request_correction")
def test_ipa_shown_on_sentence_and_feedback(mock_request, tmp_path: Path):
    mock_request.return_value = CorrectionResult(
        available=True,
        uses_expression=True,
        needs_correction=False,
        corrected=None,
        explanation="",
    )
    session = PracticeSession(vocab_dir=_ipa_vocab(tmp_path), progress_file=tmp_path / "p.md")
    session.submit_answer("receive")
    assert session.state()["ipa"] == "rɪˈsiːv"
    session.submit_sentence("I received it.", base_url="x", model="m")
    assert session.step == "feedback"
    assert session.state()["ipa"] == "rɪˈsiːv"


def test_ipa_shown_on_reveal_and_null_without_one(tmp_path: Path):
    session = PracticeSession(
        vocab_dir=_ipa_vocab(tmp_path), progress_file=tmp_path / "p.md", mode="recall-only"
    )
    session.submit_answer("wrong")
    assert session.step == "reveal"
    assert session.state()["ipa"] == "rɪˈsiːv"
    session.continue_to_next()
    session.submit_answer("wrong")
    assert session.state()["ipa"] is None


def test_no_ipa_key_on_choose_complete_empty(tmp_path: Path):
    vocab_dir = _ipa_vocab(tmp_path)
    session = PracticeSession(vocab_dir=vocab_dir, progress_file=tmp_path / "p.md", offer_choice=True)
    assert "ipa" not in session.state()
    empty_dir = tmp_path / "none"
    empty_dir.mkdir()
    empty = PracticeSession(vocab_dir=empty_dir, progress_file=tmp_path / "p.md")
    assert "ipa" not in empty.state()
    done = PracticeSession(vocab_dir=vocab_dir, progress_file=tmp_path / "p.md", mode="recall-only")
    while done.step != "complete":
        done.submit_answer("x")
        done.continue_to_next()
    assert "ipa" not in done.state()
