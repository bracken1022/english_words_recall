"""Contract tests for contracts/web-api-contract.md (spec 003)."""

from pathlib import Path
from unittest.mock import patch

from src.services.llm_client import CorrectionResult
from src.services.speech_client import TranscriptionResult
from src.web.app import create_app


def _make_client(
    tmp_path: Path,
    vocab_text: str | None = "---\nenglish: receive\nchinese: 收到\n---\n",
    offer_choice: bool = False,
):
    vocab_dir = tmp_path / "vocab"
    vocab_dir.mkdir()
    if vocab_text is not None:
        (vocab_dir / "unit1.md").write_text(vocab_text)
    app = create_app(
        vocab_dir=vocab_dir,
        progress_file=tmp_path / "progress.md",
        group=None,
        ollama_url="http://localhost:11434",
        model="qwen3:14b",
        offer_choice=offer_choice,
    )
    return app.test_client()


def test_get_state_recall_step_never_reveals_english(tmp_path: Path):
    client = _make_client(tmp_path)
    resp = client.get("/api/state")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["step"] == "recall"
    assert data["chinese"] == "收到"
    assert "accepted_expressions" not in data
    assert "receive" not in str(data)


def test_get_state_empty_pool(tmp_path: Path):
    client = _make_client(tmp_path, vocab_text=None)
    resp = client.get("/api/state")
    data = resp.get_json()
    assert data["step"] == "empty"


def test_get_state_always_has_warnings_field(tmp_path: Path):
    client = _make_client(tmp_path)
    data = client.get("/api/state").get_json()
    assert data["warnings"] == []


def test_post_answer_correct_reveals_expressions(tmp_path: Path):
    client = _make_client(tmp_path)
    resp = client.post("/api/answer", json={"answer": "receive"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["correct"] is True
    assert data["accepted_expressions"] == ["receive"]


def test_post_answer_incorrect_still_reveals_expressions(tmp_path: Path):
    client = _make_client(tmp_path)
    data = client.post("/api/answer", json={"answer": "wrong"}).get_json()
    assert data["correct"] is False
    assert data["accepted_expressions"] == ["receive"]


def test_post_answer_blank_is_incorrect_no_error(tmp_path: Path):
    client = _make_client(tmp_path)
    resp = client.post("/api/answer", json={"answer": ""})
    assert resp.status_code == 200
    assert resp.get_json()["correct"] is False


def test_post_answer_rejected_when_not_awaiting_answer(tmp_path: Path):
    client = _make_client(tmp_path)
    client.post("/api/answer", json={"answer": "receive"})  # moves to "sentence"
    resp = client.post("/api/answer", json={"answer": "receive"})
    assert resp.status_code == 409
    assert "error" in resp.get_json()


def test_post_continue_rejected_from_recall(tmp_path: Path):
    client = _make_client(tmp_path)
    resp = client.post("/api/continue")
    assert resp.status_code == 409


def test_post_continue_rejected_from_sentence(tmp_path: Path):
    client = _make_client(tmp_path)
    client.post("/api/answer", json={"answer": "receive"})
    resp = client.post("/api/continue")
    assert resp.status_code == 409


def test_post_sentence_rejected_when_not_awaiting_sentence(tmp_path: Path):
    client = _make_client(tmp_path)
    resp = client.post("/api/sentence", json={"sentence": "I received a gift."})
    assert resp.status_code == 409


@patch("src.web.session_state.request_correction")
def test_post_sentence_needs_correction(mock_request, tmp_path: Path):
    mock_request.return_value = CorrectionResult(
        available=True, uses_expression=True, needs_correction=True,
        corrected="I received a gift.", explanation="Past tense needed.",
    )
    client = _make_client(tmp_path)
    client.post("/api/answer", json={"answer": "receive"})
    resp = client.post("/api/sentence", json={"sentence": "I recieve a gift."})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["available"] is True
    assert data["needs_correction"] is True
    assert data["corrected"] == "I received a gift."
    assert data["explanation"] == "Past tense needed."


@patch("src.web.session_state.request_correction")
def test_post_sentence_already_correct(mock_request, tmp_path: Path):
    mock_request.return_value = CorrectionResult(
        available=True, uses_expression=True, needs_correction=False, corrected=None, explanation=None
    )
    client = _make_client(tmp_path)
    client.post("/api/answer", json={"answer": "receive"})
    data = client.post("/api/sentence", json={"sentence": "I received a gift."}).get_json()
    assert data["needs_correction"] is False
    assert data["available"] is True


@patch("src.web.session_state.request_correction")
def test_post_sentence_missing_expression(mock_request, tmp_path: Path):
    mock_request.return_value = CorrectionResult(
        available=True, uses_expression=False, needs_correction=False, corrected=None, explanation=None
    )
    client = _make_client(tmp_path)
    client.post("/api/answer", json={"answer": "receive"})
    data = client.post("/api/sentence", json={"sentence": "I am happy today."}).get_json()
    assert data["uses_expression"] is False


@patch("src.web.session_state.request_correction")
def test_post_sentence_unavailable(mock_request, tmp_path: Path):
    mock_request.return_value = CorrectionResult(
        available=False, uses_expression=None, needs_correction=None, corrected=None, explanation=None
    )
    client = _make_client(tmp_path)
    client.post("/api/answer", json={"answer": "receive"})
    resp = client.post("/api/sentence", json={"sentence": "I received a gift."})
    assert resp.status_code == 200
    assert resp.get_json()["available"] is False


@patch("src.web.session_state.request_correction")
def test_post_sentence_advances_step_to_feedback(mock_request, tmp_path: Path):
    mock_request.return_value = CorrectionResult(
        available=True, uses_expression=True, needs_correction=False, corrected=None, explanation=None
    )
    client = _make_client(tmp_path)
    client.post("/api/answer", json={"answer": "receive"})
    client.post("/api/sentence", json={"sentence": "I received a gift."})
    state = client.get("/api/state").get_json()
    assert state["step"] == "feedback"


def test_get_state_recall_step_has_no_answer_or_correct_fields(tmp_path: Path):
    client = _make_client(tmp_path)
    data = client.get("/api/state").get_json()
    assert "answer" not in data
    assert "correct" not in data


def test_get_state_sentence_step_includes_answer_and_correct(tmp_path: Path):
    client = _make_client(tmp_path)
    client.post("/api/answer", json={"answer": "wrong"})
    data = client.get("/api/state").get_json()
    assert data["step"] == "sentence"
    assert data["answer"] == "wrong"
    assert data["correct"] is False


@patch("src.web.session_state.request_correction")
def test_get_state_feedback_step_includes_answer_and_correct(mock_request, tmp_path: Path):
    mock_request.return_value = CorrectionResult(
        available=True, uses_expression=True, needs_correction=False, corrected=None, explanation=None
    )
    client = _make_client(tmp_path)
    client.post("/api/answer", json={"answer": "receive"})
    client.post("/api/sentence", json={"sentence": "I received a gift."})
    data = client.get("/api/state").get_json()
    assert data["step"] == "feedback"
    assert data["answer"] == "receive"
    assert data["correct"] is True


def test_post_select_rejected_when_not_choosing(tmp_path: Path):
    client = _make_client(tmp_path)  # offer_choice=False, starts in "recall"
    resp = client.post("/api/select", json={"collection": None})
    assert resp.status_code == 409
    assert "error" in resp.get_json()


def test_post_select_missing_collection_key_is_bad_request(tmp_path: Path):
    client = _make_client(
        tmp_path,
        vocab_text="---\nenglish: receive\nchinese: 收到\ngroup: unit1\n---\n",
        offer_choice=True,
    )
    resp = client.post("/api/select", json={})
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "missing 'collection'"


def test_post_select_named_collection_scopes_the_session(tmp_path: Path):
    client = _make_client(
        tmp_path,
        vocab_text=(
            "---\nenglish: receive\nchinese: 收到\ngroup: unit1\n---\n\n"
            "---\nenglish: tailor\nchinese: 裁缝\ngroup: t-words\n---\n"
        ),
        offer_choice=True,
    )
    assert client.get("/api/state").get_json()["step"] == "choose"

    resp = client.post("/api/select", json={"collection": "unit1"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["step"] == "recall"
    assert data["chinese"] == "收到"


def test_post_select_null_collection_practices_everything(tmp_path: Path):
    client = _make_client(
        tmp_path,
        vocab_text=(
            "---\nenglish: receive\nchinese: 收到\ngroup: unit1\n---\n\n"
            "---\nenglish: tailor\nchinese: 裁缝\ngroup: t-words\n---\n"
        ),
        offer_choice=True,
    )
    resp = client.post("/api/select", json={"collection": None})
    assert resp.status_code == 200
    assert resp.get_json()["step"] == "recall"


def test_post_select_does_not_touch_progress_log(tmp_path: Path):
    progress_file = tmp_path / "progress.md"
    client = _make_client(
        tmp_path,
        vocab_text="---\nenglish: receive\nchinese: 收到\ngroup: unit1\n---\n",
        offer_choice=True,
    )
    client.post("/api/select", json={"collection": "unit1"})
    assert not progress_file.exists()


def test_get_state_complete_step_can_restart_true_when_interactive(tmp_path: Path):
    client = _make_client(
        tmp_path,
        vocab_text="---\nenglish: receive\nchinese: 收到\ngroup: unit1\n---\n",
        offer_choice=True,
    )
    client.post("/api/select", json={"collection": "unit1"})
    client.post("/api/answer", json={"answer": "receive"})
    client.post("/api/skip")
    data = client.get("/api/state").get_json()
    assert data["step"] == "complete"
    assert data["can_restart"] is True


def test_get_state_complete_step_can_restart_false_when_group_locked(tmp_path: Path):
    client = _make_client(tmp_path)  # offer_choice=False, no picker at all
    client.post("/api/answer", json={"answer": "receive"})
    client.post("/api/skip")
    data = client.get("/api/state").get_json()
    assert data["step"] == "complete"
    assert data["can_restart"] is False


def test_post_restart_rejected_when_not_complete(tmp_path: Path):
    client = _make_client(
        tmp_path,
        vocab_text="---\nenglish: receive\nchinese: 收到\ngroup: unit1\n---\n",
        offer_choice=True,
    )
    resp = client.post("/api/restart")
    assert resp.status_code == 409


def test_post_restart_rejected_when_group_locked(tmp_path: Path):
    client = _make_client(tmp_path)  # offer_choice=False
    client.post("/api/answer", json={"answer": "receive"})
    client.post("/api/skip")
    assert client.get("/api/state").get_json()["step"] == "complete"
    resp = client.post("/api/restart")
    assert resp.status_code == 409


def test_post_restart_returns_to_choose(tmp_path: Path):
    client = _make_client(
        tmp_path,
        vocab_text="---\nenglish: receive\nchinese: 收到\ngroup: unit1\n---\n",
        offer_choice=True,
    )
    client.post("/api/select", json={"collection": "unit1"})
    client.post("/api/answer", json={"answer": "receive"})
    client.post("/api/skip")
    assert client.get("/api/state").get_json()["step"] == "complete"

    resp = client.post("/api/restart")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["step"] == "choose"
    assert data["collections"][0]["key"] is None


def test_get_state_reports_voice_available_true(tmp_path: Path):
    with patch("src.web.app.is_available", return_value=True):
        client = _make_client(tmp_path)
    data = client.get("/api/state").get_json()
    assert data["voice_available"] is True


def test_get_state_reports_voice_available_false(tmp_path: Path):
    with patch("src.web.app.is_available", return_value=False):
        client = _make_client(tmp_path)
    data = client.get("/api/state").get_json()
    assert data["voice_available"] is False


def test_voice_available_present_on_every_step_not_just_sentence(tmp_path: Path):
    with patch("src.web.app.is_available", return_value=True):
        client = _make_client(tmp_path, vocab_text=None)  # -> "empty" step
    data = client.get("/api/state").get_json()
    assert data["step"] == "empty"
    assert data["voice_available"] is True


@patch("src.web.app.transcribe")
def test_post_transcribe_success(mock_transcribe, tmp_path: Path):
    mock_transcribe.return_value = TranscriptionResult(available=True, text="I received a gift.")
    client = _make_client(tmp_path)
    resp = client.post("/api/transcribe", data=b"fake audio", content_type="audio/webm")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["available"] is True
    assert data["text"] == "I received a gift."


@patch("src.web.app.transcribe")
def test_post_transcribe_unavailable_is_still_200(mock_transcribe, tmp_path: Path):
    mock_transcribe.return_value = TranscriptionResult(available=False, text=None)
    client = _make_client(tmp_path)
    resp = client.post("/api/transcribe", data=b"fake audio", content_type="audio/webm")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["available"] is False
    assert data["text"] is None


@patch("src.web.app.transcribe")
def test_post_transcribe_accepted_regardless_of_practice_step(mock_transcribe, tmp_path: Path):
    """No 409 exists for this endpoint — it has no relationship to
    recall/sentence/feedback progression (research.md §3)."""
    mock_transcribe.return_value = TranscriptionResult(available=True, text="hello")
    client = _make_client(tmp_path)  # starts in "recall", not "sentence"
    resp = client.post("/api/transcribe", data=b"fake audio", content_type="audio/webm")
    assert resp.status_code == 200


def test_post_skip_rejected_when_not_awaiting_sentence(tmp_path: Path):
    client = _make_client(tmp_path)  # still in "recall"
    resp = client.post("/api/skip")
    assert resp.status_code == 409
    assert "error" in resp.get_json()


@patch("src.web.session_state.request_correction")
def test_post_skip_advances_to_next_recall_step(mock_request, tmp_path: Path):
    client = _make_client(
        tmp_path,
        vocab_text="---\nenglish: receive\nchinese: 收到\n---\n\n---\nenglish: give up\nchinese: 放弃\n---\n",
    )
    client.post("/api/answer", json={"answer": "receive"})
    resp = client.post("/api/skip")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["step"] == "recall"
    assert data["chinese"] == "放弃"
    mock_request.assert_not_called()


@patch("src.web.session_state.request_correction")
def test_post_skip_on_last_item_reaches_complete_with_tally(mock_request, tmp_path: Path):
    client = _make_client(tmp_path)  # single "receive" item
    client.post("/api/answer", json={"answer": "receive"})
    resp = client.post("/api/skip")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["step"] == "complete"
    assert data["total"] == 1
    assert data["correct"] == 1
    mock_request.assert_not_called()


@patch("src.web.session_state.request_correction")
def test_post_sentence_rejects_second_request_while_one_in_progress(mock_request, tmp_path: Path):
    """The Flask test client is synchronous/single-request, so this
    exercises the same reentrant simulation as the unit test: the mocked
    correction_fn issues a second POST /api/sentence before the first
    returns."""
    client = _make_client(tmp_path)
    client.post("/api/answer", json={"answer": "receive"})

    inner_response = {}

    def reentrant_correction(*args, **kwargs):
        inner_response["resp"] = client.post("/api/sentence", json={"sentence": "a second one"})
        return CorrectionResult(
            available=True, uses_expression=True, needs_correction=False, corrected=None, explanation=None
        )

    mock_request.side_effect = reentrant_correction

    outer_resp = client.post("/api/sentence", json={"sentence": "I received a gift."})

    assert inner_response["resp"].status_code == 409
    assert "error" in inner_response["resp"].get_json()
    assert outer_resp.status_code == 200  # the original request still completed normally


@patch("src.web.session_state.random.shuffle")
def test_post_select_random_order_shuffles_once(mock_shuffle, tmp_path: Path):
    client = _make_client(
        tmp_path,
        vocab_text=(
            "---\nenglish: receive\nchinese: 收到\ngroup: unit1\n---\n\n"
            "---\nenglish: tailor\nchinese: 裁缝\ngroup: unit1\n---\n"
        ),
        offer_choice=True,
    )
    resp = client.post("/api/select", json={"collection": "unit1", "order": "random"})
    assert resp.status_code == 200
    mock_shuffle.assert_called_once()


@patch("src.web.session_state.random.shuffle")
def test_post_select_order_absent_defaults_to_sequential(mock_shuffle, tmp_path: Path):
    client = _make_client(
        tmp_path,
        vocab_text="---\nenglish: receive\nchinese: 收到\ngroup: unit1\n---\n",
        offer_choice=True,
    )
    resp = client.post("/api/select", json={"collection": "unit1"})
    assert resp.status_code == 200
    mock_shuffle.assert_not_called()


@patch("src.web.session_state.random.shuffle")
def test_post_select_invalid_order_defaults_to_sequential(mock_shuffle, tmp_path: Path):
    client = _make_client(
        tmp_path,
        vocab_text="---\nenglish: receive\nchinese: 收到\ngroup: unit1\n---\n",
        offer_choice=True,
    )
    resp = client.post("/api/select", json={"collection": "unit1", "order": "not-a-real-value"})
    assert resp.status_code == 200
    mock_shuffle.assert_not_called()


def test_post_select_missing_collection_is_400_regardless_of_order(tmp_path: Path):
    client = _make_client(
        tmp_path,
        vocab_text="---\nenglish: receive\nchinese: 收到\ngroup: unit1\n---\n",
        offer_choice=True,
    )
    resp = client.post("/api/select", json={"order": "random"})
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "missing 'collection'"
