"""Contract tests for contracts/remove-word-api.md (spec 020)."""

import hashlib
import io
from pathlib import Path

import pytest

from src.models.account import Account
from src.web.app import create_app

SHARED = (
    "---\nenglish: river\nchinese: 河\ngroup: shared-set\n---\n\n"
    "---\nenglish: lake\nchinese: 湖\ngroup: shared-set\n---\n"
)
UNIT1 = "zealous, 热心的\nrent, 租金\ntyre, 轮胎\n"


def _app(tmp_path: Path, accounts=True, store=True):
    vocab = tmp_path / "vocab"
    vocab.mkdir(exist_ok=True)
    (vocab / "shared.md").write_text(SHARED, encoding="utf-8")
    kwargs = {}
    if accounts:
        kwargs["accounts"] = [
            Account("lily", "pw-lily", "Lily", tmp_path / "p-lily.md"),
            Account("weibo", "pw-weibo", "Weibo", tmp_path / "p-weibo.md"),
        ]
    if store:
        kwargs["word_lists_dir"] = tmp_path / "word-lists"
    return create_app(vocab_dir=vocab, progress_file=tmp_path / "p.md", offer_choice=True, **kwargs)


def _login(app, user="lily"):
    client = app.test_client()
    if user:
        client.post("/api/login", json={"username": user, "password": f"pw-{user}"})
    return client


def _upload_and_select(client):
    data = {"file": (io.BytesIO(UNIT1.encode()), "unit1.csv")}
    assert client.post("/api/word-lists", data=data, content_type="multipart/form-data").status_code == 200
    client.post("/api/select", json={"collection": "unit1", "mode": "recall-only"})


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _counts(client) -> dict:
    client.post("/api/end")
    state = client.get("/api/state").get_json()
    return {c["label"]: c["count"] for c in state["collections"]}


def test_remove_from_own_list(tmp_path):
    client = _login(_app(tmp_path))
    _upload_and_select(client)
    resp = client.post("/api/remove-word")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["removed"] == {"english": "zealous", "chinese": "热心的"}
    assert data["undo"] is True
    assert data["state"]["step"] == "recall"
    assert data["state"]["chinese"] == "租金"
    text = (tmp_path / "word-lists" / "lily" / "unit1.md").read_text(encoding="utf-8")
    assert "zealous" not in text
    lists = client.get("/api/word-lists").get_json()["lists"]
    assert lists[0]["word_count"] == 2
    assert _counts(client)["unit1"] == 2


def test_remove_shared_word_hides_it_for_this_learner_only(tmp_path):
    app = _app(tmp_path)
    shared = tmp_path / "vocab" / "shared.md"
    before = sha(shared)
    lily = _login(app, "lily")
    lily.post("/api/select", json={"collection": "shared-set", "mode": "recall-only"})
    resp = lily.post("/api/remove-word")
    assert resp.get_json()["removed"]["english"] == "river"
    assert sha(shared) == before
    assert _counts(lily)["shared-set"] == 1
    lily.post("/api/select", json={"collection": "shared-set", "mode": "recall-only"})
    assert lily.get("/api/state").get_json()["chinese"] == "湖"
    weibo = _login(app, "weibo")
    assert _counts(weibo)["shared-set"] == 2


def test_wrong_step_is_409(tmp_path):
    client = _login(_app(tmp_path))
    resp = client.post("/api/remove-word")
    assert resp.status_code == 409
    assert resp.get_json() == {"error": "There's no word to remove right now."}


@pytest.mark.parametrize("accounts, store", [(True, False), (False, False)])
def test_no_store_is_404(tmp_path, accounts, store):
    app = _app(tmp_path, accounts=accounts, store=store)
    client = _login(app) if accounts else app.test_client()
    assert client.post("/api/remove-word").status_code == 404
    assert client.post("/api/undo-remove").status_code == 404


def test_login_required(tmp_path):
    client = _login(_app(tmp_path), user=None)
    assert client.post("/api/remove-word").status_code == 401


def test_file_error_changes_nothing(tmp_path, monkeypatch):
    client = _login(_app(tmp_path))
    _upload_and_select(client)
    path = tmp_path / "word-lists" / "lily" / "unit1.md"
    before = sha(path)
    from src.services import word_lists

    def boom(*_a, **_k):
        raise OSError("disk full")

    monkeypatch.setattr(word_lists.os, "replace", boom)
    resp = client.post("/api/remove-word")
    monkeypatch.undo()
    assert resp.status_code == 500
    assert resp.get_json() == {"error": "Couldn't remove the word; nothing was changed."}
    assert sha(path) == before
    assert client.get("/api/state").get_json()["chinese"] == "热心的"


def test_word_already_gone_is_removed_without_undo(tmp_path):
    client = _login(_app(tmp_path))
    _upload_and_select(client)
    path = tmp_path / "word-lists" / "lily" / "unit1.md"
    path.write_text(path.read_text(encoding="utf-8").replace("zealous", "other"), encoding="utf-8")
    data = client.post("/api/remove-word").get_json()
    assert data["undo"] is False
    assert data["state"]["chinese"] == "租金"


# --- US2: undo ------------------------------------------------------------------


def test_undo_own_list_is_byte_identical(tmp_path):
    client = _login(_app(tmp_path))
    _upload_and_select(client)
    path = tmp_path / "word-lists" / "lily" / "unit1.md"
    before = sha(path)
    client.post("/api/remove-word")
    resp = client.post("/api/undo-remove")
    assert resp.status_code == 200
    state = resp.get_json()
    assert (state["step"], state["chinese"]) == ("recall", "热心的")
    assert sha(path) == before
    again = client.post("/api/undo-remove")
    assert again.status_code == 409
    assert again.get_json() == {"error": "Nothing to undo."}


def test_undo_shared_word_unhides_it(tmp_path):
    client = _login(_app(tmp_path))
    client.post("/api/select", json={"collection": "shared-set", "mode": "recall-only"})
    client.post("/api/remove-word")
    assert client.post("/api/undo-remove").status_code == 200
    assert _counts(client)["shared-set"] == 2
    hidden = (tmp_path / "word-lists" / "lily" / ".hidden-shared.json").read_text("utf-8")
    assert "river" not in hidden


def test_undo_window_closed_after_next_answer(tmp_path):
    client = _login(_app(tmp_path))
    _upload_and_select(client)
    client.post("/api/remove-word")
    client.post("/api/answer", json={"answer": "rent"})
    assert client.post("/api/undo-remove").status_code == 409
