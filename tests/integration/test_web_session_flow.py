"""Integration tests for the full web session flow (spec 003)."""

from pathlib import Path
from unittest.mock import patch

from src.services.llm_client import CorrectionResult
from src.services.speech_client import TranscriptionResult
from src.web.app import create_app


def _make_client(tmp_path: Path, vocab_text: str | None = None, offer_choice: bool = False):
    if vocab_text is None:
        vocab_text = (
            "---\nenglish: receive\nchinese: 收到\n---\n\n"
            "---\nenglish: give up\nchinese: 放弃\n---\n"
        )
    vocab_dir = tmp_path / "vocab"
    vocab_dir.mkdir()
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


def test_recall_only_cycle_hides_english_until_submitted(tmp_path: Path):
    client = _make_client(tmp_path)

    state = client.get("/api/state").get_json()
    assert state["step"] == "recall"
    assert "receive" not in str(state)

    answer_resp = client.post("/api/answer", json={"answer": "receive"}).get_json()
    assert answer_resp["correct"] is True

    state = client.get("/api/state").get_json()
    assert state["step"] == "sentence"
    assert "receive" in state["accepted_expressions"]


@patch("src.web.session_state.request_correction")
def test_full_recall_sentence_feedback_cycle_writes_progress_log(mock_request, tmp_path: Path):
    mock_request.return_value = CorrectionResult(
        available=True, uses_expression=True, needs_correction=True,
        corrected="I received a gift.", explanation="Past tense needed.",
    )

    vocab_dir = tmp_path / "vocab"
    vocab_dir.mkdir()
    (vocab_dir / "unit1.md").write_text("---\nenglish: receive\nchinese: 收到\n---\n")
    progress_file = tmp_path / "progress.md"
    app = create_app(vocab_dir=vocab_dir, progress_file=progress_file, group=None,
                      ollama_url="http://localhost:11434", model="qwen3:14b")
    client = app.test_client()

    client.post("/api/answer", json={"answer": "receive"})
    client.post("/api/sentence", json={"sentence": "I recieve a gift."})

    state = client.get("/api/state").get_json()
    assert state["step"] == "feedback"
    assert state["feedback"]["corrected"] == "I received a gift."

    progress_text = progress_file.read_text(encoding="utf-8")
    assert "item: receive" in progress_text
    assert "answer: receive" in progress_text
    assert "correct: true" in progress_text
    assert "sentence: I recieve a gift." in progress_text
    assert "corrected: I received a gift." in progress_text

    client.post("/api/continue")
    state = client.get("/api/state").get_json()
    assert state["step"] == "complete"


@patch("src.web.session_state.request_correction")
def test_skipped_word_counts_correctly_and_is_distinguishable_in_history(mock_request, tmp_path: Path):
    """Spec 006 US2: a skipped word's recall outcome still counts toward
    the end-of-session tally, and its progress-log entry is distinguishable
    from a word where a sentence was actually submitted."""
    mock_request.return_value = CorrectionResult(
        available=True, uses_expression=True, needs_correction=False, corrected=None, explanation=None
    )
    vocab_text = (
        "---\nenglish: receive\nchinese: 收到\n---\n\n"
        "---\nenglish: give up\nchinese: 放弃\n---\n"
    )
    progress_file = tmp_path / "progress.md"
    vocab_dir = tmp_path / "vocab"
    vocab_dir.mkdir()
    (vocab_dir / "unit1.md").write_text(vocab_text)
    app = create_app(vocab_dir=vocab_dir, progress_file=progress_file, group=None,
                      ollama_url="http://localhost:11434", model="qwen3:14b")
    client = app.test_client()

    # Word 1: answered correctly, sentence actually submitted.
    client.post("/api/answer", json={"answer": "receive"})
    client.post("/api/sentence", json={"sentence": "I received a gift."})
    client.post("/api/continue")

    # Word 2: answered incorrectly, sentence step skipped.
    client.post("/api/answer", json={"answer": "wrong"})
    resp = client.post("/api/skip")
    state = resp.get_json()

    assert state["step"] == "complete"
    assert state["total"] == 2
    assert state["correct"] == 1  # only word 1 was recalled correctly; skip doesn't change this

    progress_text = progress_file.read_text(encoding="utf-8")
    completed_block = progress_text[: progress_text.index("give up")]
    skipped_block = progress_text[progress_text.index("give up") :]
    assert "sentence:" in completed_block and "feedback:" in completed_block
    assert "sentence:" not in skipped_block and "feedback:" not in skipped_block


def test_full_choose_practice_complete_restart_loop(tmp_path: Path):
    """Spec 007: choose -> recall -> ... -> complete -> restart -> choose,
    through the real Flask test client."""
    vocab_text = (
        "---\nenglish: receive\nchinese: 收到\ngroup: unit1\n---\n\n"
        "---\nenglish: tailor\nchinese: 裁缝\ngroup: t-words\n---\n"
    )
    client = _make_client(tmp_path, vocab_text=vocab_text, offer_choice=True)

    state = client.get("/api/state").get_json()
    assert state["step"] == "choose"
    assert {c["key"] for c in state["collections"]} == {None, "unit1", "t-words"}

    client.post("/api/select", json={"collection": "unit1"})
    assert client.get("/api/state").get_json()["step"] == "recall"

    client.post("/api/answer", json={"answer": "receive"})
    resp = client.post("/api/skip")
    state = resp.get_json()
    assert state["step"] == "complete"
    assert state["can_restart"] is True

    resp = client.post("/api/restart")
    assert resp.status_code == 200
    assert resp.get_json()["step"] == "choose"


def test_group_locked_web_ui_never_shows_choose(tmp_path: Path):
    """A --group-started server behaves exactly as it did before spec 007:
    no "choose" step, and both new endpoints reject."""
    vocab_dir = tmp_path / "vocab"
    vocab_dir.mkdir()
    (vocab_dir / "unit1.md").write_text("---\nenglish: receive\nchinese: 收到\ngroup: unit1\n---\n")
    app = create_app(
        vocab_dir=vocab_dir,
        progress_file=tmp_path / "progress.md",
        group="unit1",
        ollama_url="http://localhost:11434",
        model="qwen3:14b",
        offer_choice=True,  # a real group always wins, even if this is also set
    )
    client = app.test_client()

    assert client.get("/api/state").get_json()["step"] == "recall"
    assert client.post("/api/select", json={"collection": None}).status_code == 409
    assert client.post("/api/restart").status_code == 409


@patch("src.web.app.transcribe")
@patch("src.web.session_state.request_correction")
def test_full_record_transcribe_review_submit_flow(mock_request, mock_transcribe, tmp_path: Path):
    """Spec 009: transcribed text is submitted through the exact same
    POST /api/sentence path as typed text, indistinguishable in the
    progress log."""
    mock_request.return_value = CorrectionResult(
        available=True, uses_expression=True, needs_correction=False, corrected=None, explanation=None
    )
    mock_transcribe.return_value = TranscriptionResult(
        available=True, text="I received a gift yesterday."
    )
    progress_file = tmp_path / "progress.md"
    vocab_dir = tmp_path / "vocab"
    vocab_dir.mkdir()
    (vocab_dir / "unit1.md").write_text("---\nenglish: receive\nchinese: 收到\n---\n")
    app = create_app(vocab_dir=vocab_dir, progress_file=progress_file, group=None,
                      ollama_url="http://localhost:11434", model="qwen3:14b")
    client = app.test_client()

    client.post("/api/answer", json={"answer": "receive"})

    transcribe_resp = client.post("/api/transcribe", data=b"fake audio", content_type="audio/webm")
    assert transcribe_resp.status_code == 200
    recognized_text = transcribe_resp.get_json()["text"]
    assert recognized_text == "I received a gift yesterday."

    # The learner reviews the recognized text, then submits it exactly as
    # they would a typed sentence — same endpoint, no new code path.
    client.post("/api/sentence", json={"sentence": recognized_text})

    state = client.get("/api/state").get_json()
    assert state["step"] == "feedback"

    progress_text = progress_file.read_text(encoding="utf-8")
    assert "sentence: I received a gift yesterday." in progress_text


def test_default_host_is_lan_reachable(tmp_path: Path):
    from src.web.__main__ import build_arg_parser

    args = build_arg_parser().parse_args([])
    assert args.host == "0.0.0.0"


def test_custom_host_and_port_are_honored(tmp_path: Path):
    from src.web.__main__ import build_arg_parser

    args = build_arg_parser().parse_args(["--host", "127.0.0.1", "--port", "9999"])
    assert args.host == "127.0.0.1"
    assert args.port == 9999


def test_malformed_vocab_block_surfaces_warning_valid_item_still_loads(tmp_path: Path):
    vocab_dir = tmp_path / "vocab"
    vocab_dir.mkdir()
    (vocab_dir / "unit1.md").write_text(
        "---\nchinese: missing english field\n---\n\n---\nenglish: give up\nchinese: 放弃\n---\n"
    )
    app = create_app(vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md", group=None,
                      ollama_url="http://localhost:11434", model="qwen3:14b")
    client = app.test_client()

    state = client.get("/api/state").get_json()
    assert state["step"] == "recall"
    assert state["chinese"] == "放弃"
    assert len(state["warnings"]) == 1


def test_empty_vocab_pool_shows_empty_step_no_error(tmp_path: Path):
    vocab_dir = tmp_path / "vocab"
    vocab_dir.mkdir()
    app = create_app(vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md", group=None,
                      ollama_url="http://localhost:11434", model="qwen3:14b")
    client = app.test_client()

    resp = client.get("/api/state")
    assert resp.status_code == 200
    assert resp.get_json()["step"] == "empty"


def test_word_feedback_and_sentence_prompt_both_present_after_submission(tmp_path: Path):
    """spec 004 US1 Acceptance Scenario 2: word feedback and the
    sentence-practice section must both be present at once — checked at
    the data level (GET /api/state carries both), independent of how the
    front end lays them out."""
    client = _make_client(tmp_path, vocab_text="---\nenglish: receive\nchinese: 收到\n---\n")
    client.post("/api/answer", json={"answer": "wrong"})
    state = client.get("/api/state").get_json()
    assert state["step"] == "sentence"
    assert state["correct"] is False
    assert state["answer"] == "wrong"
    assert "accepted_expressions" in state  # the sentence prompt's own data


def test_word_feedback_survives_a_simulated_reload_mid_sentence_step(tmp_path: Path):
    """A 'reload' is just another GET /api/state on the same session; if
    the answer/correct fields were only ever returned by the transient
    POST /api/answer response, this would fail."""
    client = _make_client(tmp_path, vocab_text="---\nenglish: receive\nchinese: 收到\n---\n")
    client.post("/api/answer", json={"answer": "receive"})

    reload_state = client.get("/api/state").get_json()
    assert reload_state["step"] == "sentence"
    assert reload_state["answer"] == "receive"
    assert reload_state["correct"] is True
