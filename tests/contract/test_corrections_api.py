"""Contract tests for contracts/corrections-api.md (spec 023): `corrected`
in the practice state, GET /api/corrections and POST
/api/corrections/undo. The Qwen check is always a fake."""

import logging
import threading
from pathlib import Path

import pytest

from src.models.account import Account
from src.services.qwen_client import QwenError
from src.services.word_check import WordCheck
from src.web.app import create_app

SHARED = (
    "---\nenglish: tailor\nipa: ˈteɪlə\npos: [v.]\nalternates: []\nchinese: 裁缝\ngroup: t-words\n---\n\n"
    "---\nenglish: tidy\nipa: ˈtaɪdi\npos: [adj.]\nalternates: []\nchinese: 整洁的\ngroup: t-words\n---\n"
)
OWN = (
    "---\nenglish: zealous\nipa: ˈzeləs\npos: [n.]\nalternates: []\nchinese: 嫉妒的\ngroup: unit1\n---\n\n"
    "---\nenglish: rent\nipa: rent\npos: [n.]\nalternates: []\nchinese: 租金\ngroup: unit1\n---\n"
)
ZEALOUS = WordCheck("ˈzeləs", "热心的；狂热的", ["adj."])
SECRET_PROMPT_LINE = "You check dictionary data"


class FakeCheck:
    def __init__(self, answers=None):
        self.answers = answers or {}
        self.calls = []
        self.gate: threading.Event | None = None

    def __call__(self, english, ipa, chinese, pos, dialect):
        self.calls.append(english)
        if self.gate is not None:
            self.gate.wait(5)
        answer = self.answers.get(english)
        if isinstance(answer, Exception):
            raise answer
        return answer or WordCheck(ipa, chinese, list(pos))


def _folders(tmp_path: Path, own: bool = True):
    vocab = tmp_path / "vocab"
    vocab.mkdir(exist_ok=True)
    (vocab / "T_words.md").write_text(SHARED, encoding="utf-8")
    if own:
        folder = tmp_path / "wl" / "lily"
        folder.mkdir(parents=True, exist_ok=True)
        if not (folder / "unit1.md").exists():  # a second app reuses the files
            (folder / "unit1.md").write_text(OWN, encoding="utf-8")
    return vocab


def _app(tmp_path: Path, check=None, own: bool = True):
    vocab = _folders(tmp_path, own)
    return create_app(
        vocab_dir=vocab,
        progress_file=tmp_path / "p.md",
        offer_choice=True,
        accounts=[
            Account("lily", "pw", "Lily", tmp_path / "pl.md"),
            Account("weibo", "pw", "Weibo", tmp_path / "pw.md"),
        ],
        word_lists_dir=tmp_path / "wl",
        correction_check=check,
    )


def _client(app, user="lily"):
    client = app.test_client()
    client.post("/api/login", json={"username": user, "password": "pw"})
    return client


def _practise(app, client, collection="unit1", answer="zealous"):
    client.post("/api/select", json={"collection": collection, "mode": "recall-only"})
    if app.correction_service is not None:
        app.correction_service.wait_all(5)
    client.post("/api/answer", json={"answer": answer + "x"})  # wrong: goes to reveal
    return client.get("/api/state").get_json()


# --- state ---------------------------------------------------------------------------


def test_reveal_shows_corrected_values(tmp_path):
    app = _app(tmp_path, FakeCheck({"zealous": ZEALOUS}))
    client = _client(app)
    state = _practise(app, client)
    assert state["step"] == "reveal"
    assert state["chinese"] == "热心的；狂热的"
    assert state["pos"] == ["adj."]
    assert state["corrected"] == ["chinese", "pos"]


def test_recall_has_no_corrected_and_unchanged_word_has_empty_list(tmp_path):
    app = _app(tmp_path, FakeCheck())
    client = _client(app)
    client.post("/api/select", json={"collection": "unit1", "mode": "recall-only"})
    assert "corrected" not in client.get("/api/state").get_json()
    app.correction_service.wait_all(5)
    client.post("/api/answer", json={"answer": "nope"})
    assert client.get("/api/state").get_json()["corrected"] == []


# --- GET /api/corrections ----------------------------------------------------------------


def test_list_corrections(tmp_path):
    app = _app(tmp_path, FakeCheck({"zealous": ZEALOUS}))
    client = _client(app)
    _practise(app, client)
    body = client.get("/api/corrections").get_json()
    assert body["enabled"] is True and body["paused"] is None
    entries = body["corrections"]
    assert [e["field"] for e in entries] == ["chinese", "pos"]
    entry = entries[0]
    assert set(entry) == {
        "id",
        "scope",
        "english",
        "list",
        "field",
        "old",
        "new",
        "at",
        "undone",
        "can_undo",
    }
    assert (entry["scope"], entry["english"], entry["list"]) == ("own", "zealous", "unit1.md")
    assert (entry["old"], entry["new"]) == ("嫉妒的", "热心的；狂热的")
    assert entries[1]["old"] == ["n."] and entries[1]["new"] == ["adj."]
    assert entry["undone"] is False and entry["can_undo"] is True


def test_paused_reason_is_shown(tmp_path):
    app = _app(tmp_path, FakeCheck({"zealous": QwenError("unavailable")}))
    client = _client(app)
    _practise(app, client)
    paused = client.get("/api/corrections").get_json()["paused"]
    assert paused["reason"] == "Qwen could not be reached."
    assert paused["until"].endswith("Z")


def test_no_key_means_off_and_practice_unchanged(tmp_path):
    app = _app(tmp_path)  # conftest clears DASHSCOPE_API_KEY
    assert app.correction_service is None or app.correction_service.enabled is False
    client = _client(app)
    state = _practise(app, client)
    assert state["chinese"] == "嫉妒的" and state["corrected"] == []
    body = client.get("/api/corrections").get_json()
    assert body == {"enabled": False, "paused": None, "corrections": []}


def test_key_in_the_environment_turns_it_on(tmp_path, monkeypatch):
    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-test")
    app = _app(tmp_path)
    assert app.correction_service.enabled is True


def test_login_required(tmp_path):
    app = _app(tmp_path, FakeCheck())
    client = app.test_client()
    response = client.get("/api/corrections")
    assert response.status_code == 401
    assert response.get_json() == {"error": "login required"}
    assert client.post("/api/corrections/undo", json={"id": "x"}).status_code == 401


def test_nothing_secret_is_returned_or_logged(tmp_path, monkeypatch, caplog):
    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-very-secret")
    fake = FakeCheck({"zealous": QwenError("bad_reply")})
    app = _app(tmp_path, fake)
    client = _client(app)
    with caplog.at_level(logging.DEBUG):
        _practise(app, client)
        text = client.get("/api/corrections").get_data(as_text=True)
    for leaked in ("sk-very-secret", SECRET_PROMPT_LINE):
        assert leaked not in text
        assert leaked not in caplog.text
    assert "嫉妒的" not in caplog.text  # word values are never logged


# --- POST /api/corrections/undo (US2) -----------------------------------------------------


def _corrected(tmp_path):
    app = _app(tmp_path, FakeCheck({"zealous": ZEALOUS}))
    client = _client(app)
    _practise(app, client)
    entries = client.get("/api/corrections").get_json()["corrections"]
    return app, client, entries


def test_undo_restores_and_returns_the_fields(tmp_path):
    _, client, entries = _corrected(tmp_path)
    response = client.post("/api/corrections/undo", json={"id": entries[0]["id"]})
    assert response.status_code == 200
    assert response.get_json() == {"undone": ["chinese", "pos"]}
    # The current word shows the old values at once.
    state = client.get("/api/state").get_json()
    assert (state["chinese"], state["pos"], state["corrected"]) == ("嫉妒的", ["n."], [])
    after = client.get("/api/corrections").get_json()["corrections"]
    assert all(e["undone"] and not e["can_undo"] for e in after)


def test_undo_unknown_id_is_404(tmp_path):
    _, client, _ = _corrected(tmp_path)
    response = client.post("/api/corrections/undo", json={"id": "ffffffffffff"})
    assert response.status_code == 404
    assert response.get_json() == {"error": "That correction wasn't found."}


def test_undo_twice_is_409(tmp_path):
    _, client, entries = _corrected(tmp_path)
    client.post("/api/corrections/undo", json={"id": entries[0]["id"]})
    response = client.post("/api/corrections/undo", json={"id": entries[1]["id"]})
    assert response.status_code == 409
    assert response.get_json() == {"error": "That correction was already undone."}


def test_undo_after_an_edit_is_409(tmp_path):
    _, client, entries = _corrected(tmp_path)
    own = tmp_path / "wl" / "lily" / "unit1.md"
    own.write_text(
        own.read_text(encoding="utf-8").replace("热心的；狂热的", "热心的"), encoding="utf-8"
    )
    response = client.post("/api/corrections/undo", json={"id": entries[0]["id"]})
    assert response.status_code == 409
    assert response.get_json() == {"error": "That word has changed since, so it can't be undone."}


@pytest.mark.parametrize("body", [None, {}, {"id": 5}, {"id": ""}, ["x"]])
def test_undo_needs_an_id(tmp_path, body):
    _, client, _ = _corrected(tmp_path)
    response = client.post("/api/corrections/undo", json=body)
    assert response.status_code == 400
    assert response.get_json() == {"error": "id is required"}


def test_undo_works_without_a_key(tmp_path):
    _, _, entries = _corrected(tmp_path)
    keyless = _app(tmp_path)  # same folders, no key, no fake
    client = _client(keyless)
    body = client.get("/api/corrections").get_json()
    assert body["enabled"] is False and len(body["corrections"]) == 2
    assert client.post("/api/corrections/undo", json={"id": entries[0]["id"]}).status_code == 200


# --- shared sets (US3) -------------------------------------------------------------------

TAILOR = WordCheck("ˈteɪlə", "裁缝；定做（衣服）", ["n.", "v."])


def test_shared_corrections_listed_and_undone_by_shared_learners(tmp_path):
    app = _app(tmp_path, FakeCheck({"tailor": TAILOR}))
    weibo = _client(app, "weibo")  # practises the shared sets
    state = _practise(app, weibo, collection="t-words", answer="tailor")
    assert state["chinese"] == "裁缝；定做（衣服）" and state["corrected"] == ["chinese", "pos"]
    entries = weibo.get("/api/corrections").get_json()["corrections"]
    assert {e["scope"] for e in entries} == {"shared"}

    lily = _client(app, "lily")  # own lists: shared records aren't hers
    assert lily.get("/api/corrections").get_json()["corrections"] == []
    response = lily.post("/api/corrections/undo", json={"id": entries[0]["id"]})
    assert response.status_code == 404

    assert weibo.post("/api/corrections/undo", json={"id": entries[0]["id"]}).status_code == 200
    assert weibo.get("/api/state").get_json()["chinese"] == "裁缝"
