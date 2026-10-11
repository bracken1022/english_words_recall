"""Integration tests for multiple learner accounts (spec 015). One Flask
test client stands for one browser/device."""

from pathlib import Path

from src.models.account import Account
from src.models.practice_attempt import PracticeAttempt
from src.services.progress_log import append_attempt, read_attempts
from src.web.app import create_app

VOCAB = "---\nenglish: receive\nchinese: 收到\n---\n\n---\nenglish: give up\nchinese: 放弃\n---\n"


def _make_app(tmp_path: Path, vocab_text: str = VOCAB, **kwargs):
    vocab_dir = tmp_path / "vocab"
    vocab_dir.mkdir()
    (vocab_dir / "unit1.md").write_text(vocab_text, encoding="utf-8")
    accounts = [
        Account("weibo", "pw-weibo", "Weibo", tmp_path / "progress.md"),
        Account("lily", "pw-lily", "Lily", tmp_path / "progress-lily.md"),
    ]
    options = {"offer_choice": True}
    options.update(kwargs)
    return create_app(
        vocab_dir=vocab_dir,
        progress_file=tmp_path / "progress.md",
        accounts=accounts,
        **options,
    )


def _login(client, username):
    resp = client.post("/api/login", json={"username": username, "password": f"pw-{username}"})
    assert resp.status_code == 200


def _existing_attempt() -> PracticeAttempt:
    return PracticeAttempt(
        timestamp="2026-09-01T10:00:00+00:00", item="old word", answer="old", correct=True
    )


# --- US1: separate histories ------------------------------------------------


def test_each_account_writes_only_its_own_history(tmp_path: Path):
    progress = tmp_path / "progress.md"
    append_attempt(progress, _existing_attempt())
    app = _make_app(tmp_path)

    a = app.test_client()
    _login(a, "weibo")
    a.post("/api/select", json={"collection": None, "mode": "recall-only"})
    a.post("/api/answer", json={"answer": "receive"})
    a.post("/api/continue")

    b = app.test_client()
    _login(b, "lily")
    b.post("/api/select", json={"collection": None, "mode": "recall-only"})
    b.post("/api/answer", json={"answer": "wrong"})
    b.post("/api/continue")

    weibo_attempts, _ = read_attempts(progress)
    lily_attempts, _ = read_attempts(tmp_path / "progress-lily.md")
    assert [x.answer for x in weibo_attempts] == ["old", "receive"]
    assert [x.answer for x in lily_attempts] == ["wrong"]


def test_second_account_never_touches_pre_existing_history(tmp_path: Path):
    progress = tmp_path / "progress.md"
    append_attempt(progress, _existing_attempt())
    before = progress.read_bytes()
    app = _make_app(tmp_path)

    b = app.test_client()
    _login(b, "lily")
    b.post("/api/select", json={"collection": None, "mode": "recall-only"})
    b.post("/api/answer", json={"answer": "receive"})
    b.post("/api/continue")

    assert progress.read_bytes() == before
    assert len(read_attempts(tmp_path / "progress-lily.md")[0]) == 1


# --- US2: practicing at the same time --------------------------------------

GROUPED_VOCAB = (
    "---\nenglish: receive\nchinese: 收到\ngroup: unit1\n---\n\n"
    "---\nenglish: give up\nchinese: 放弃\ngroup: unit1\n---\n\n"
    "---\nenglish: accept\nchinese: 接受\ngroup: unit2\n---\n"
)


def _two_learners(tmp_path: Path):
    app = _make_app(tmp_path, vocab_text=GROUPED_VOCAB)
    a, b = app.test_client(), app.test_client()
    _login(a, "weibo")
    _login(b, "lily")
    a.post("/api/select", json={"collection": "unit1", "order": "sequential", "mode": "example"})
    b.post("/api/select", json={"collection": "unit2", "mode": "recall-only"})
    return a, b


def _state(client) -> dict:
    return client.get("/api/state").get_json()


def test_interleaved_sessions_stay_independent(tmp_path: Path):
    a, b = _two_learners(tmp_path)
    assert (_state(a)["total"], _state(b)["total"]) == (2, 1)

    a.post("/api/answer", json={"answer": "receive"})
    assert _state(a)["step"] == "reveal"
    assert _state(b)["step"] == "recall"
    assert _state(b)["chinese"] == "接受"

    b.post("/api/answer", json={"answer": "accept"})
    b.post("/api/continue")
    b_state = _state(b)
    assert b_state["step"] == "complete"
    assert b_state["correct"] == 1

    a_state = _state(a)
    assert a_state["step"] == "reveal"
    assert a_state["position"] == 1
    assert a_state["total"] == 2


def test_example_belongs_only_to_its_account(tmp_path: Path):
    # Spec 021 replaced the per-account sentence review with examples.
    a, b = _two_learners(tmp_path)
    a.post("/api/answer", json={"answer": "receive"})

    a_state, b_state = _state(a), _state(b)
    assert a_state["step"] == "reveal"
    assert "example_status" in a_state
    assert "example" not in b_state
    assert "example_status" not in b_state


def test_one_account_ending_its_session_leaves_the_other_alone(tmp_path: Path):
    a, b = _two_learners(tmp_path)
    a.post("/api/answer", json={"answer": "receive"})
    before = _state(a)
    assert b.post("/api/end").status_code == 200
    assert _state(b)["step"] == "choose"
    after = _state(a)
    assert (after["step"], after["position"]) == (before["step"], before["position"])


def test_same_account_on_two_devices_shares_one_session(tmp_path: Path):
    app = _make_app(tmp_path)
    phone, laptop = app.test_client(), app.test_client()
    _login(phone, "weibo")
    _login(laptop, "weibo")
    phone.post("/api/select", json={"collection": None, "mode": "recall-only"})
    phone.post("/api/answer", json={"answer": "receive"})
    assert _state(laptop)["step"] == _state(phone)["step"] == "reveal"
    assert _state(laptop)["position"] == 1


# --- US3: log out and switch accounts --------------------------------------


def test_logout_mid_reveal_discards_word_and_starts_fresh(tmp_path: Path):
    app = _make_app(tmp_path)
    client = app.test_client()
    _login(client, "weibo")
    client.post("/api/select", json={"collection": None, "mode": "example"})
    client.post("/api/answer", json={"answer": "receive"})
    assert _state(client)["step"] == "reveal"

    client.post("/api/logout")
    progress = tmp_path / "progress.md"
    assert not progress.exists() or read_attempts(progress)[0] == []

    _login(client, "weibo")
    assert _state(client)["step"] == "choose"


def test_logout_while_reveal_is_held_writes_nothing(tmp_path: Path):
    app = _make_app(tmp_path)
    client = app.test_client()
    _login(client, "weibo")
    client.post("/api/select", json={"collection": None, "mode": "recall-only"})
    client.post("/api/answer", json={"answer": "wrong"})
    assert _state(client)["step"] == "reveal"
    client.post("/api/logout")
    assert not (tmp_path / "progress.md").exists()


def test_switching_accounts_on_one_device(tmp_path: Path):
    app = _make_app(tmp_path)
    client = app.test_client()
    _login(client, "weibo")
    client.post("/api/select", json={"collection": None, "mode": "example"})
    client.post("/api/answer", json={"answer": "receive"})
    client.post("/api/logout")

    _login(client, "lily")
    state = _state(client)
    assert state["step"] == "choose"
    assert state["account"]["username"] == "lily"
    assert not (tmp_path / "progress-lily.md").exists()


def test_logout_resets_a_group_locked_session(tmp_path: Path):
    app = _make_app(
        tmp_path,
        vocab_text=GROUPED_VOCAB,
        group="unit1",
        offer_choice=False,
    )
    client = app.test_client()
    _login(client, "weibo")
    client.post("/api/answer", json={"answer": "receive"})
    client.post("/api/logout")

    _login(client, "weibo")
    state = _state(client)
    assert (state["step"], state["position"]) == ("recall", 1)
