"""Contract tests for contracts/web-api-contract.md (spec 003)."""

from pathlib import Path
from unittest.mock import patch

from src.services.llm_client import CorrectionResult
from src.web.app import create_app


def _make_client(tmp_path: Path, vocab_text: str | None = "---\nenglish: receive\nchinese: 收到\n---\n"):
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
