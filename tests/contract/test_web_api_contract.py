"""Contract tests for contracts/web-api-contract.md (spec 003)."""

from pathlib import Path
from unittest.mock import patch

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
    client.post("/api/answer", json={"answer": "receive"})  # moves to "reveal"
    resp = client.post("/api/answer", json={"answer": "receive"})
    assert resp.status_code == 409
    assert "error" in resp.get_json()


def test_post_continue_rejected_from_recall(tmp_path: Path):
    client = _make_client(tmp_path)
    resp = client.post("/api/continue")
    assert resp.status_code == 409


def test_get_state_recall_step_has_no_answer_or_correct_fields(tmp_path: Path):
    client = _make_client(tmp_path)
    data = client.get("/api/state").get_json()
    assert "answer" not in data
    assert "correct" not in data


def test_get_state_reveal_step_includes_answer_and_correct(tmp_path: Path):
    client = _make_client(tmp_path)
    client.post("/api/answer", json={"answer": "receive"})
    data = client.get("/api/state").get_json()
    assert data["step"] == "reveal"
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
    client.post("/api/continue")
    data = client.get("/api/state").get_json()
    assert data["step"] == "complete"
    assert data["can_restart"] is True


def test_get_state_complete_step_can_restart_false_when_group_locked(tmp_path: Path):
    client = _make_client(tmp_path)  # offer_choice=False, no picker at all
    client.post("/api/answer", json={"answer": "receive"})
    client.post("/api/continue")
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
    client.post("/api/continue")
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
    client.post("/api/continue")
    assert client.get("/api/state").get_json()["step"] == "complete"

    resp = client.post("/api/restart")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["step"] == "choose"
    assert data["collections"][0]["key"] is None


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


def test_post_select_recall_only_mode_is_accepted(tmp_path: Path):
    client = _make_client(
        tmp_path,
        vocab_text="---\nenglish: receive\nchinese: 收到\ngroup: unit1\n---\n",
        offer_choice=True,
    )
    resp = client.post("/api/select", json={"collection": "unit1", "mode": "recall-only"})
    assert resp.status_code == 200
    assert resp.get_json()["step"] == "recall"


def test_post_select_recall_only_then_answer_reveals_without_example(tmp_path: Path):
    client = _make_client(
        tmp_path,
        vocab_text="---\nenglish: receive\nchinese: 收到\ngroup: unit1\n---\n",
        offer_choice=True,
    )
    client.post("/api/select", json={"collection": "unit1", "mode": "recall-only"})
    resp = client.post("/api/answer", json={"answer": "receive"})
    assert resp.status_code == 200
    # Broadsheet redesign: even a correct recall-only answer waits in
    # "reveal" until the learner continues; spec 021: with no example.
    state = client.get("/api/state").get_json()
    assert state["step"] == "reveal"
    assert state["example_status"] == "off"

    state = client.post("/api/continue").get_json()
    assert state["step"] == "complete"
    assert state["total"] == 1
    assert state["correct"] == 1


def test_post_select_mode_absent_defaults_to_example(tmp_path: Path):
    client = _make_client(
        tmp_path,
        vocab_text="---\nenglish: receive\nchinese: 收到\ngroup: unit1\n---\n",
        offer_choice=True,
    )
    client.post("/api/select", json={"collection": "unit1"})
    client.post("/api/answer", json={"answer": "receive"})
    state = client.get("/api/state").get_json()
    assert (state["step"], state["mode"]) == ("reveal", "example")


def test_post_select_invalid_mode_defaults_to_example(tmp_path: Path):
    client = _make_client(
        tmp_path,
        vocab_text="---\nenglish: receive\nchinese: 收到\ngroup: unit1\n---\n",
        offer_choice=True,
    )
    client.post("/api/select", json={"collection": "unit1", "mode": "not-a-real-value"})
    client.post("/api/answer", json={"answer": "receive"})
    state = client.get("/api/state").get_json()
    assert (state["step"], state["mode"]) == ("reveal", "example")


def test_post_answer_wrong_in_recall_only_mode_lands_on_reveal(tmp_path: Path):
    client = _make_client(
        tmp_path,
        vocab_text="---\nenglish: receive\nchinese: 收到\ngroup: unit1\n---\n",
        offer_choice=True,
    )
    client.post("/api/select", json={"collection": "unit1", "mode": "recall-only"})
    resp = client.post("/api/answer", json={"answer": "wrong"})
    assert resp.status_code == 200

    state = client.get("/api/state").get_json()
    assert state["step"] == "reveal"
    assert state["answer"] == "wrong"
    assert state["correct"] is False
    assert state["accepted_expressions"] == ["receive"]


def test_post_continue_from_reveal_records_attempt_and_advances(tmp_path: Path):
    progress_file = tmp_path / "progress.md"
    client = _make_client(
        tmp_path,
        vocab_text="---\nenglish: receive\nchinese: 收到\ngroup: unit1\n---\n",
        offer_choice=True,
    )
    client.post("/api/select", json={"collection": "unit1", "mode": "recall-only"})
    client.post("/api/answer", json={"answer": "wrong"})
    assert not progress_file.exists()

    resp = client.post("/api/continue")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["step"] == "complete"
    assert data["total"] == 1
    assert data["correct"] == 0

    text = progress_file.read_text(encoding="utf-8")
    assert "item: receive" in text
    assert "answer: wrong" in text
    assert "correct: false" in text
    assert "sentence:" not in text
    assert "feedback:" not in text


def test_post_continue_rejected_from_recall_still_409_regardless_of_mode(tmp_path: Path):
    client = _make_client(
        tmp_path,
        vocab_text="---\nenglish: receive\nchinese: 收到\ngroup: unit1\n---\n",
        offer_choice=True,
    )
    client.post("/api/select", json={"collection": "unit1", "mode": "recall-only"})
    resp = client.post("/api/continue")
    assert resp.status_code == 409


# --- Broadsheet redesign endpoints ---


def test_post_end_returns_to_choose(tmp_path: Path):
    client = _make_client(tmp_path, offer_choice=True)
    client.post("/api/select", json={"collection": None})
    client.post("/api/answer", json={"answer": "wrong"})

    resp = client.post("/api/end")

    assert resp.status_code == 200
    assert resp.get_json()["step"] == "choose"


def test_post_end_rejected_when_group_locked(tmp_path: Path):
    client = _make_client(tmp_path)
    resp = client.post("/api/end")
    assert resp.status_code == 409


# --- spec 024: missed words at "complete" (contracts/state-complete.md) ----------

MISSED_VOCAB = (
    "---\nenglish: receive\nchinese: 收到\nipa: rɪˈsiːv\npos: [v.]\ngroup: unit1\n---\n\n"
    "---\nenglish: rent\nchinese: 租金\ngroup: unit1\n---\n\n"
    "---\nenglish: tyre\nchinese: 轮胎\ngroup: unit1\n---\n"
)


def _finish(client, answers):
    client.post("/api/select", json={"collection": "unit1", "mode": "recall-only"})
    for answer in answers:
        client.post("/api/answer", json={"answer": answer})
        client.post("/api/continue")
    return client.get("/api/state").get_json()


def test_complete_state_lists_missed_words(tmp_path: Path):
    client = _make_client(tmp_path, vocab_text=MISSED_VOCAB, offer_choice=True)
    data = _finish(client, ["recieve", "", "tyre"])
    assert data["step"] == "complete"
    assert data["missed"] == [
        {
            "english": "receive",
            "ipa": "rɪˈsiːv",
            "pos": ["v."],
            "chinese": "收到",
            "answer": "recieve",
            "shown": False,
        },
        {
            "english": "rent",
            "ipa": None,
            "pos": [],
            "chinese": "租金",
            "answer": None,
            "shown": True,
        },
    ]
    assert len(data["missed"]) == data["total"] - data["correct"]


def test_complete_state_missed_is_empty_when_all_right(tmp_path: Path):
    client = _make_client(tmp_path, vocab_text=MISSED_VOCAB, offer_choice=True)
    assert _finish(client, ["receive", "rent", "tyre"])["missed"] == []


def test_missed_is_absent_before_complete(tmp_path: Path):
    client = _make_client(tmp_path, vocab_text=MISSED_VOCAB, offer_choice=True)
    client.post("/api/select", json={"collection": "unit1", "mode": "recall-only"})
    assert "missed" not in client.get("/api/state").get_json()
    client.post("/api/answer", json={"answer": "x"})
    assert "missed" not in client.get("/api/state").get_json()


def test_each_account_sees_only_its_own_missed_words(tmp_path: Path):
    from src.models.account import Account

    vocab_dir = tmp_path / "vocab"
    vocab_dir.mkdir()
    (vocab_dir / "unit1.md").write_text(MISSED_VOCAB, encoding="utf-8")
    app = create_app(
        vocab_dir=vocab_dir,
        progress_file=tmp_path / "progress.md",
        offer_choice=True,
        accounts=[
            Account("weibo", "pw1", "Weibo", tmp_path / "p1.md"),
            Account("lily", "pw2", None, tmp_path / "p2.md"),
        ],
        word_lists_dir=tmp_path / "wl",
    )
    weibo, lily = app.test_client(), app.test_client()
    weibo.post("/api/login", json={"username": "weibo", "password": "pw1"})
    lily.post("/api/login", json={"username": "lily", "password": "pw2"})
    weibo_missed = _finish(weibo, ["x", "rent", "tyre"])["missed"]
    lily_missed = _finish(lily, ["receive", "rent", "y"])["missed"]
    assert [(m["english"], m["answer"]) for m in weibo_missed] == [("receive", "x")]
    assert [(m["english"], m["answer"]) for m in lily_missed] == [("tyre", "y")]
    assert weibo.get("/api/state").get_json()["missed"] == weibo_missed
