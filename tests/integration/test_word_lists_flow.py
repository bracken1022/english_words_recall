"""Integration tests for personal word lists (spec 016). One Flask test
client stands for one browser/device."""

import io
from pathlib import Path

import pytest
from flask import Flask

from src.models.account import Account
from src.services.progress_log import read_attempts
from src.web import __main__ as web_main
from src.web.app import create_app

SHARED = (
    "---\nenglish: river\nchinese: 河\ngroup: shared-set\n---\n\n"
    "---\nenglish: lake\nchinese: 湖\ngroup: shared-set\n---\n"
)
UNIT1 = "English, Chinese\nreceive, 收到\nbroken\n"
T_WORDS = (
    "---\nenglish: tablet\nchinese: 平板\ngroup: t-words\n---\n\n"
    "---\nenglish: tailor\nchinese: 裁缝\ngroup: t-words\n---\n"
)


def _make_app(tmp_path: Path, **kwargs):
    vocab_dir = tmp_path / "vocab"
    vocab_dir.mkdir(exist_ok=True)
    (vocab_dir / "shared.md").write_text(SHARED, encoding="utf-8")
    accounts = [
        Account("weibo", "pw-weibo", "Weibo", tmp_path / "progress.md"),
        Account("lily", "pw-lily", "Lily", tmp_path / "progress-lily.md"),
    ]
    return create_app(
        vocab_dir=vocab_dir,
        progress_file=tmp_path / "progress.md",
        offer_choice=True,
        accounts=accounts,
        word_lists_dir=tmp_path / "word-lists",
        **kwargs,
    )


def _login(app, username):
    client = app.test_client()
    resp = client.post("/api/login", json={"username": username, "password": f"pw-{username}"})
    assert resp.status_code == 200
    return client


def _upload(client, text, filename, replace=None):
    data = {"file": (io.BytesIO(text.encode("utf-8")), filename)}
    if replace is not None:
        data["replace"] = replace
    return client.post("/api/word-lists", data=data, content_type="multipart/form-data")


def _state(client) -> dict:
    return client.get("/api/state").get_json()


def _collections(client) -> list[tuple[str, int]]:
    return [(c["label"], c["count"]) for c in _state(client)["collections"]]


# --- US1 ---------------------------------------------------------------------


def test_upload_appears_immediately_and_can_be_practiced(tmp_path: Path):
    app = _make_app(tmp_path)
    lily = _login(app, "lily")
    assert ("shared-set", 2) in _collections(lily)

    assert _upload(lily, UNIT1, "unit1.csv").status_code == 200
    assert _state(lily)["step"] == "choose"
    assert _collections(lily) == [("Practice everything", 1), ("unit1", 1)]

    lily.post("/api/select", json={"collection": "unit1", "mode": "recall-only"})
    assert lily.post("/api/answer", json={"answer": "receive"}).get_json()["correct"] is True
    lily.post("/api/continue")
    attempts, _ = read_attempts(tmp_path / "progress-lily.md")
    assert [a.item for a in attempts] == ["receive"]


def test_markdown_upload_is_named_after_the_file(tmp_path: Path):
    app = _make_app(tmp_path)
    weibo = _login(app, "weibo")
    resp = _upload(weibo, T_WORDS, "T_words.md")
    assert resp.get_json()["name"] == "T_words"
    assert _collections(weibo) == [("Practice everything", 2), ("T_words", 2)]


@pytest.fixture
def recorded_run(monkeypatch):
    calls: list[dict] = []
    monkeypatch.setattr(Flask, "run", lambda self, *a, **k: calls.append({"app": self, **k}))
    return calls


def test_word_lists_dir_flag_and_banner(tmp_path, monkeypatch, capsys, recorded_run):
    assert web_main.build_arg_parser().parse_args([]).word_lists_dir == Path("word-lists")
    vocab = tmp_path / "vocab"
    vocab.mkdir()
    (vocab / "shared.md").write_text(SHARED, encoding="utf-8")
    accounts_file = tmp_path / "accounts.yml"
    accounts_file.write_text("accounts:\n  - username: lily\n    password: pw-lily\n")
    lists_dir = tmp_path / "lists"
    monkeypatch.setattr(
        "sys.argv",
        [
            "src.web",
            "--vocab-dir",
            str(vocab),
            "--progress-file",
            str(tmp_path / "progress.md"),
            "--accounts-file",
            str(accounts_file),
            "--word-lists-dir",
            str(lists_dir),
        ],
    )
    web_main.main()
    assert f"Word lists: {lists_dir}" in capsys.readouterr().out

    client = recorded_run[0]["app"].test_client()
    client.post("/api/login", json={"username": "lily", "password": "pw-lily"})
    assert _upload(client, UNIT1, "unit1.csv").status_code == 200
    assert (lists_dir / "lily" / "unit1.md").exists()


# --- US2: each account practices only its own words --------------------------


def test_each_account_sees_only_its_own_lists(tmp_path: Path):
    app = _make_app(tmp_path)
    lily, weibo = _login(app, "lily"), _login(app, "weibo")
    _upload(lily, UNIT1, "unit1.csv")
    _upload(weibo, T_WORDS, "T_words.md")
    assert _collections(lily) == [("Practice everything", 1), ("unit1", 1)]
    assert _collections(weibo) == [("Practice everything", 2), ("T_words", 2)]


def test_account_without_uploads_keeps_shared_folder(tmp_path: Path):
    app = _make_app(tmp_path)
    lily, weibo = _login(app, "lily"), _login(app, "weibo")
    _upload(lily, UNIT1, "unit1.csv")
    assert _collections(weibo) == [("Practice everything", 2), ("shared-set", 2)]


def test_practice_history_stays_with_its_account(tmp_path: Path):
    app = _make_app(tmp_path)
    lily = _login(app, "lily")
    _upload(lily, "receive, 收到\ngive up, 放弃\n", "unit1.csv")
    lily.post("/api/select", json={"collection": "unit1", "mode": "recall-only"})
    for answer in ("receive", "give up"):
        lily.post("/api/answer", json={"answer": answer})
        lily.post("/api/continue")
    attempts, _ = read_attempts(tmp_path / "progress-lily.md")
    assert [a.item for a in attempts] == ["receive", "give up"]
    assert not (tmp_path / "progress.md").exists()


def test_lists_survive_a_restart(tmp_path: Path):
    app = _make_app(tmp_path)
    _upload(_login(app, "lily"), UNIT1, "unit1.csv")
    restarted = _make_app(tmp_path)
    assert _collections(_login(restarted, "lily")) == [("Practice everything", 1), ("unit1", 1)]
    assert ("shared-set", 2) in _collections(_login(restarted, "weibo"))


def test_same_list_name_for_two_accounts(tmp_path: Path):
    app = _make_app(tmp_path)
    lily, weibo = _login(app, "lily"), _login(app, "weibo")
    _upload(lily, "receive, 收到\n", "unit1.csv")
    _upload(weibo, "tablet, 平板\ntailor, 裁缝\n", "unit1.csv")
    assert _collections(lily) == [("Practice everything", 1), ("unit1", 1)]
    assert _collections(weibo) == [("Practice everything", 2), ("unit1", 2)]
    assert (tmp_path / "word-lists" / "lily" / "unit1.md").exists()
    assert (tmp_path / "word-lists" / "weibo" / "unit1.md").exists()


def test_upload_mid_session_does_not_disturb_it(tmp_path: Path):
    app = _make_app(tmp_path)
    phone, laptop = _login(app, "lily"), _login(app, "lily")
    phone.post("/api/select", json={"collection": "shared-set", "mode": "example"})
    before = _state(phone)
    _upload(laptop, UNIT1, "unit1.csv")
    after = _state(phone)
    assert (after["step"], after["position"], after["total"], after["chinese"]) == (
        before["step"],
        before["position"],
        before["total"],
        before["chinese"],
    )
    phone.post("/api/end")
    assert _collections(phone) == [("Practice everything", 1), ("unit1", 1)]


# --- US3: replace and delete --------------------------------------------------


def test_replace_mid_session_keeps_session_and_history(tmp_path: Path):
    app = _make_app(tmp_path)
    phone, laptop = _login(app, "lily"), _login(app, "lily")
    _upload(phone, "receive, 收到\ngive up, 放弃\n", "unit1.csv")
    phone.post("/api/select", json={"collection": "unit1", "mode": "recall-only"})
    phone.post("/api/answer", json={"answer": "receive"})
    phone.post("/api/continue")

    resp = _upload(laptop, "tablet, 平板\ntailor, 裁缝\ntale, 故事\n", "unit1.csv", replace="true")
    assert resp.status_code == 200
    state = _state(phone)
    assert (state["step"], state["position"], state["total"], state["chinese"]) == (
        "recall",
        2,
        2,
        "放弃",
    )
    phone.post("/api/end")
    assert _collections(phone) == [("Practice everything", 3), ("unit1", 3)]
    attempts, _ = read_attempts(tmp_path / "progress-lily.md")
    assert [a.item for a in attempts] == ["receive"]


def test_deleting_last_list_returns_to_shared_words(tmp_path: Path):
    app = _make_app(tmp_path)
    lily = _login(app, "lily")
    _upload(lily, UNIT1, "unit1.csv")
    lily.post("/api/select", json={"collection": "unit1", "mode": "recall-only"})
    lily.post("/api/answer", json={"answer": "receive"})
    lily.post("/api/continue")
    lily.post("/api/restart")
    history_before = (tmp_path / "progress-lily.md").read_bytes()

    assert lily.delete("/api/word-lists/unit1").status_code == 200
    state = _state(lily)
    assert state["word_source"] == "shared"
    assert _collections(lily) == [("Practice everything", 2), ("shared-set", 2)]
    assert (tmp_path / "progress-lily.md").read_bytes() == history_before
