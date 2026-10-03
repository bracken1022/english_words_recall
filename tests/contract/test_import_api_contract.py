"""Contract tests for contracts/import-api-contract.md (spec 018): uploads
become a pending import, are enriched in the background through the
(mocked) local model, and are written as vocabulary Markdown only when
the learner confirms."""

import hashlib
import io
import json
import os
import re
import threading
from pathlib import Path
from unittest.mock import patch

import pytest
import requests
import yaml

from src.models.account import Account
from src.web.app import create_app

SHARED = "---\nenglish: river\nchinese: 河\ngroup: shared-set\n---\n"

REPLIES = {
    "zealous": {"chinese": "热心的；热情的",
                "alternates": ["enthusiastic"]},
    "tyre": {"chinese": "轮胎", "alternates": ["tire"]},
    "epitomise": {"chinese": "是…的典范",
                  "alternates": ["epitomize"]},
    "receive": {"chinese": "收到；接受", "alternates": []},
}


class _FakeResponse:
    def __init__(self, status_code, json_data=None):
        self.status_code = status_code
        self._json_data = json_data or {}

    def json(self):
        return self._json_data


class FakeOllama:
    """Answers each enrichment request from a word -> reply table."""

    def __init__(self, replies=None):
        self.replies = dict(REPLIES if replies is None else replies)
        self.words: list[str] = []

    def __call__(self, url, json=None, timeout=None):
        user = json["messages"][-1]["content"]
        word = re.search(r'English: "(.*)"', user).group(1)
        self.words.append(word)
        reply = self.replies[word]
        if callable(reply):
            reply = reply()
        if isinstance(reply, Exception):
            raise reply
        if isinstance(reply, _FakeResponse):
            return reply
        content = reply if isinstance(reply, str) else _json_dumps(reply)
        return _FakeResponse(200, {"message": {"role": "assistant", "content": content}})


def _json_dumps(data):
    return json.dumps(data, ensure_ascii=False)


@pytest.fixture
def ollama():
    fake = FakeOllama()
    with patch("src.services.llm_client.requests.post", side_effect=fake):
        yield fake


def ACCOUNTS(tmp_path):
    return [
        Account("weibo", "pw-weibo", "Weibo", tmp_path / "progress.md"),
        Account("lily", "pw-lily", "Lily", tmp_path / "progress-lily.md"),
    ]


def make_app(tmp_path: Path):
    vocab_dir = tmp_path / "vocab"
    vocab_dir.mkdir(exist_ok=True)
    (vocab_dir / "shared.md").write_text(SHARED, encoding="utf-8")
    return create_app(
        vocab_dir=vocab_dir,
        progress_file=tmp_path / "progress.md",
        offer_choice=True,
        accounts=ACCOUNTS(tmp_path),
        word_lists_dir=tmp_path / "word-lists",
    )


def login(app, username="lily"):
    client = app.test_client()
    if username:
        resp = client.post("/api/login", json={"username": username, "password": f"pw-{username}"})
        assert resp.status_code == 200
    return client


def account(tmp_path, username="lily"):
    return next(a for a in ACCOUNTS(tmp_path) if a.username == username)


def start_import(client, text, filename="z-words.txt", discard_pending=None, raw=None):
    data = {"file": (io.BytesIO(raw if raw is not None else text.encode("utf-8")), filename)}
    if discard_pending is not None:
        data["discard_pending"] = discard_pending
    return client.post("/api/word-lists/import", data=data, content_type="multipart/form-data")


def finish(app, tmp_path, username="lily"):
    assert app.enrichment_runner.wait(account(tmp_path, username), 5)


def imported(client):
    return client.get("/api/word-lists/import").get_json()["import"]


def word_files(tmp_path, username="lily"):
    return sorted(p.name for p in (tmp_path / "word-lists" / username).glob("*.md"))


def blocks(path: Path):
    text = path.read_text(encoding="utf-8")
    return [yaml.safe_load(chunk) for chunk in re.findall(r"^---\n(.*?)\n---$", text, re.DOTALL | re.MULTILINE)]


# --- login guard -----------------------------------------------------------


@pytest.mark.parametrize(
    "method, path",
    [
        ("get", "/api/word-lists/import"),
        ("post", "/api/word-lists/import"),
        ("post", "/api/word-lists/import/confirm"),
        ("post", "/api/word-lists/import/retry"),
        ("post", "/api/word-lists/import/choice"),
        ("delete", "/api/word-lists/import"),
    ],
)
def test_routes_require_login(tmp_path, method, path):
    client = login(make_app(tmp_path), username=None)
    resp = getattr(client, method)(path)
    assert resp.status_code == 401
    assert resp.get_json() == {"error": "login required"}


# --- POST /api/word-lists/import --------------------------------------------


def test_missing_file(tmp_path):
    client = login(make_app(tmp_path))
    resp = client.post("/api/word-lists/import", data={}, content_type="multipart/form-data")
    assert resp.status_code == 400
    assert resp.get_json() == {"error": "Choose a file to upload."}


def test_unsupported_type(tmp_path):
    resp = start_import(login(make_app(tmp_path)), "x", filename="z.xlsx")
    assert resp.status_code == 415


def test_too_large(tmp_path):
    resp = start_import(login(make_app(tmp_path)), "", raw=b"a\n" * (600 * 1024))
    assert resp.status_code == 413


def test_no_english_words(tmp_path):
    resp = start_import(login(make_app(tmp_path)), "# only a comment\n, 收到\n")
    assert resp.status_code == 422
    data = resp.get_json()
    assert data["error"].startswith("No words found. Put one English word per line")
    assert data["skipped"] == ["line 2: no English word"]


def test_too_many_words(tmp_path):
    resp = start_import(login(make_app(tmp_path)), "w\n" * 5001)
    assert resp.status_code == 422


def test_accepted_import_is_running_and_writes_no_list(tmp_path, ollama):
    app = make_app(tmp_path)
    client = login(app)
    resp = start_import(client, "zealous\ntyre\nepitomise\n")
    assert resp.status_code == 202
    state = resp.get_json()["import"]
    assert state["status"] in ("running", "completed")
    assert state["total"] == 3
    assert state["list_name"] == "z-words"
    assert state["source_filename"] == "z-words.txt"
    finish(app, tmp_path)
    assert word_files(tmp_path) == []
    assert client.get("/api/word-lists").get_json()["lists"] == []


def test_get_import(tmp_path, ollama):
    app = make_app(tmp_path)
    client = login(app)
    assert client.get("/api/word-lists/import").get_json() == {"import": None}
    start_import(client, "zealous\ntyre\nepitomise\n")
    finish(app, tmp_path)
    state = imported(client)
    assert state["status"] == "completed"
    assert state["done"] == 3
    assert [i["english"] for i in state["items"]] == ["zealous", "tyre", "epitomise"]
    zealous, tyre, epitomise = state["items"]
    assert zealous["alternates"] == []
    assert zealous["dropped_alternates"] == ["enthusiastic"]
    assert tyre["alternates"] == ["tire"]
    assert epitomise["alternates"] == ["epitomize"]
    assert zealous["ipa"] == "ˈzeləs"


# --- POST /api/word-lists/import/confirm -------------------------------------


def test_confirm_saves_markdown_list(tmp_path, ollama):
    app = make_app(tmp_path)
    client = login(app)
    start_import(client, "zealous\ntyre\nepitomise\n")
    finish(app, tmp_path)

    resp = client.post("/api/word-lists/import/confirm", json={})
    assert resp.status_code == 200
    assert resp.get_json() == {
        "name": "z-words",
        "replaced": False,
        "added": 3,
        "updated": 0,
        "left_out": 0,
        "first_list": True,
        "applies_now": True,
    }
    path = tmp_path / "word-lists" / "lily" / "z-words.md"
    saved = blocks(path)
    assert [b["english"] for b in saved] == ["zealous", "tyre", "epitomise"]
    assert all(b["group"] == "z-words" for b in saved)
    assert list(saved[1]) == ["english", "ipa", "alternates", "chinese", "group"]
    assert saved[1]["alternates"] == ["tire"]
    assert not (tmp_path / "word-lists" / "lily" / ".pending-import.json").exists()

    lists = client.get("/api/word-lists").get_json()["lists"]
    assert [(entry["name"], entry["word_count"]) for entry in lists] == [("z-words", 3)]
    assert client.get("/api/state").get_json()["word_source"] == "own"

    before = path.read_bytes()
    again = client.post("/api/word-lists/import/confirm", json={})
    assert again.status_code == 404
    assert again.get_json() == {"error": "Nothing to save."}
    assert path.read_bytes() == before


def test_confirm_existing_name_needs_replace(tmp_path, ollama):
    app = make_app(tmp_path)
    client = login(app)
    start_import(client, "zealous\n")
    finish(app, tmp_path)
    client.post("/api/word-lists/import/confirm", json={})
    path = tmp_path / "word-lists" / "lily" / "z-words.md"
    before = path.read_bytes()

    start_import(client, "tyre\n")
    finish(app, tmp_path)
    resp = client.post("/api/word-lists/import/confirm", json={})
    assert resp.status_code == 409
    assert resp.get_json() == {"exists": True, "name": "z-words"}
    assert path.read_bytes() == before

    resp = client.post("/api/word-lists/import/confirm", json={"replace": True})
    assert resp.status_code == 200
    assert resp.get_json()["replaced"] is True
    assert [b["english"] for b in blocks(path)] == ["tyre"]


def test_discard(tmp_path, ollama):
    app = make_app(tmp_path)
    client = login(app)
    start_import(client, "zealous\n")
    finish(app, tmp_path)
    resp = client.delete("/api/word-lists/import")
    assert resp.status_code == 200
    assert resp.get_json() == {"discarded": True}
    assert not (tmp_path / "word-lists" / "lily" / ".pending-import.json").exists()
    assert client.delete("/api/word-lists/import").status_code == 404
    assert imported(client) is None


def test_model_cannot_name_or_rename_anything(tmp_path, ollama):
    ollama.replies["zealous"] = {**REPLIES["zealous"], "group": "evil", "english": "other",
                                 "file": "../../x.md"}
    app = make_app(tmp_path)
    client = login(app)
    start_import(client, "zealous\n")
    finish(app, tmp_path)
    client.post("/api/word-lists/import/confirm", json={})
    assert word_files(tmp_path) == ["z-words.md"]
    (block,) = blocks(tmp_path / "word-lists" / "lily" / "z-words.md")
    assert block["english"] == "zealous"
    assert block["group"] == "z-words"


# --- US2: retry, conflicts, partial saves, failures ---------------------------


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Gate:
    """Makes the fake model block on one word until released."""

    def __init__(self, fake: FakeOllama, word: str):
        self.started = threading.Event()
        self.release = threading.Event()
        original = fake.replies[word]

        def blocking():
            self.started.set()
            self.release.wait(5)
            return original

        fake.replies[word] = blocking


def test_retry_routes(tmp_path, ollama):
    ollama.replies["tyre"] = _FakeResponse(500)
    app = make_app(tmp_path)
    client = login(app)
    assert client.post("/api/word-lists/import/retry", json={}).status_code == 404
    assert client.post("/api/word-lists/import/retry", json={}).get_json() == {
        "error": "Nothing to retry."
    }

    start_import(client, "zealous\ntyre\n")
    finish(app, tmp_path)
    state = imported(client)
    assert state["status"] == "partially_failed"
    assert state["items"][1]["error"] == "the local AI gave an unusable answer"

    for body in ({"index": 0}, {"index": 7}, {"index": "x"}):
        resp = client.post("/api/word-lists/import/retry", json=body)
        assert resp.status_code == 400
        assert resp.get_json() == {"error": "That word can't be retried."}

    ollama.replies["tyre"] = REPLIES["tyre"]
    resp = client.post("/api/word-lists/import/retry", json={"index": 1})
    assert resp.status_code == 202
    assert resp.get_json()["import"]["status"] == "running"
    finish(app, tmp_path)
    assert imported(client)["status"] == "completed"


def test_retry_and_confirm_while_running(tmp_path, ollama):
    gate = Gate(ollama, "tyre")
    app = make_app(tmp_path)
    client = login(app)
    start_import(client, "zealous\ntyre\n")
    assert gate.started.wait(5)

    resp = client.post("/api/word-lists/import/retry", json={})
    assert resp.status_code == 200
    assert resp.get_json()["import"]["status"] == "running"
    resp = client.post("/api/word-lists/import/confirm", json={})
    assert resp.status_code == 409
    assert resp.get_json() == {"error": "Still enriching — wait until it finishes."}

    gate.release.set()
    finish(app, tmp_path)
    assert ollama.words.count("tyre") == 1
    assert client.post("/api/word-lists/import/confirm", json={}).status_code == 200


def test_second_import_needs_discard(tmp_path, ollama):
    app = make_app(tmp_path)
    client = login(app)
    start_import(client, "zealous\n")
    finish(app, tmp_path)
    first = imported(client)

    resp = start_import(client, "tyre\n", filename="t-words.txt")
    assert resp.status_code == 409
    data = resp.get_json()
    assert data["pending"] is True
    assert data["import"] == first
    assert imported(client) == first

    resp = start_import(client, "tyre\n", filename="t-words.txt", discard_pending="true")
    assert resp.status_code == 202
    finish(app, tmp_path)
    assert imported(client)["list_name"] == "t-words"


def test_discard_pending_cancels_running_worker(tmp_path, ollama):
    gate = Gate(ollama, "zealous")
    app = make_app(tmp_path)
    client = login(app)
    start_import(client, "zealous\ntyre\n")
    assert gate.started.wait(5)
    threading.Timer(0.2, gate.release.set).start()
    resp = start_import(client, "epitomise\n", filename="e.txt", discard_pending="true")
    assert resp.status_code == 202
    finish(app, tmp_path)
    state = imported(client)
    assert state["list_name"] == "e"
    assert [i["english"] for i in state["items"]] == ["epitomise"]
    assert "tyre" not in ollama.words


def test_partially_failed_confirm_saves_the_rest(tmp_path, ollama):
    ollama.replies["tyre"] = "not json"
    app = make_app(tmp_path)
    client = login(app)
    start_import(client, "zealous\ntyre\nepitomise\n")
    finish(app, tmp_path)
    resp = client.post("/api/word-lists/import/confirm", json={})
    assert resp.status_code == 200
    assert resp.get_json()["added"] == 2
    assert resp.get_json()["left_out"] == 1
    saved = blocks(tmp_path / "word-lists" / "lily" / "z-words.md")
    assert [b["english"] for b in saved] == ["zealous", "epitomise"]


def test_nothing_ready_is_422(tmp_path, ollama):
    ollama.replies["tyre"] = "not json"
    app = make_app(tmp_path)
    client = login(app)
    start_import(client, "tyre\n")
    finish(app, tmp_path)
    resp = client.post("/api/word-lists/import/confirm", json={})
    assert resp.status_code == 422
    assert resp.get_json() == {"error": "No words are ready to save."}


def test_failed_save_changes_nothing(tmp_path, ollama, monkeypatch):
    app = make_app(tmp_path)
    client = login(app)
    start_import(client, "zealous\n")
    finish(app, tmp_path)
    client.post("/api/word-lists/import/confirm", json={})
    folder = tmp_path / "word-lists" / "lily"
    (folder / "unit1.md").write_text("---\nenglish: receive\nchinese: 收到\n---\n", "utf-8")
    hashes = {p.name: sha(p) for p in folder.glob("*.md")}

    start_import(client, "tyre\n")
    finish(app, tmp_path)
    from src.services import word_lists

    real_replace = os.replace
    calls = {"n": 0}

    def flaky_replace(src, dst):
        calls["n"] += 1
        if calls["n"] == 1:
            raise OSError("disk full")
        return real_replace(src, dst)

    monkeypatch.setattr(word_lists.os, "replace", flaky_replace)
    resp = client.post("/api/word-lists/import/confirm", json={"replace": True})
    monkeypatch.setattr(word_lists.os, "replace", real_replace)

    assert resp.status_code == 500
    assert resp.get_json() == {"error": "Couldn't save the list; nothing was changed."}
    assert {p.name: sha(p) for p in folder.glob("*.md")} == hashes
    assert [p.name for p in folder.iterdir() if p.suffix in (".tmp", ".bak")] == []
    assert imported(client)["items"][0]["english"] == "tyre"


def test_ollama_down_keeps_everything(tmp_path, ollama):
    for word in ("zealous", "tyre"):
        ollama.replies[word] = requests.ConnectionError()
    app = make_app(tmp_path)
    client = login(app)
    folder = tmp_path / "word-lists" / "lily"
    folder.mkdir(parents=True)
    (folder / "unit1.md").write_text("---\nenglish: receive\nchinese: 收到\n---\n", "utf-8")
    before = sha(folder / "unit1.md")

    assert start_import(client, "zealous\ntyre\n").status_code == 202
    finish(app, tmp_path)
    state = imported(client)
    assert state["status"] == "failed"
    assert state["failure_reason"] == "Local AI unavailable — start Ollama, then press Retry."
    assert [i["state"] for i in state["items"]] == ["waiting", "waiting"]
    assert sha(folder / "unit1.md") == before
    assert sorted(p.name for p in folder.glob("*.md")) == ["unit1.md"]

    ollama.replies.update({w: REPLIES[w] for w in ("zealous", "tyre")})
    assert client.post("/api/word-lists/import/retry", json={}).status_code == 202
    finish(app, tmp_path)
    assert imported(client)["status"] == "completed"


# --- US3: existing entries ----------------------------------------------------

UNIT1 = (
    "---\nenglish: receive\nipa: rɪˈsiːv\nalternates:\n- accept\nchinese: 收到\ngroup: unit1\n---\n\n"
    "---\nenglish: give up\nipa: 42\nalternates: []\nchinese: 放弃\ngroup: unit1\n---\n"
)


def _with_unit1(tmp_path):
    folder = tmp_path / "word-lists" / "lily"
    folder.mkdir(parents=True)
    (folder / "unit1.md").write_text(UNIT1, encoding="utf-8")
    return folder / "unit1.md"


def _import_receive(tmp_path, ollama, text="receive\nzealous\n"):
    ollama.replies["receive"] = {
        "chinese": "接收；收到",
        "alternates": [],
    }
    app = make_app(tmp_path)
    client = login(app)
    start_import(client, text)
    finish(app, tmp_path)
    return client


def test_choice_route(tmp_path, ollama):
    _with_unit1(tmp_path)
    client = _import_receive(tmp_path, ollama)
    state = imported(client)
    receive = state["items"][0]
    assert receive["existing"]["source"] == "own"
    assert receive["existing"]["list"] == "unit1"
    assert receive["choice"] == "keep"

    resp = client.post("/api/word-lists/import/choice", json={"index": 0, "choice": "update"})
    assert resp.status_code == 200
    assert resp.get_json()["import"]["items"][0]["choice"] == "update"

    for body in ({"index": 1, "choice": "update"}, {"index": 0, "choice": "maybe"}, {}):
        resp = client.post("/api/word-lists/import/choice", json=body)
        assert resp.status_code == 400
        assert resp.get_json() == {"error": "That word has no entry to update."}


def test_choice_without_import_is_404(tmp_path):
    client = login(make_app(tmp_path))
    resp = client.post("/api/word-lists/import/choice", json={"index": 0, "choice": "keep"})
    assert resp.status_code == 404


def test_keep_leaves_existing_entry_untouched(tmp_path, ollama):
    unit1 = _with_unit1(tmp_path)
    before = sha(unit1)
    client = _import_receive(tmp_path, ollama)
    resp = client.post("/api/word-lists/import/confirm", json={})
    data = resp.get_json()
    assert (data["added"], data["updated"], data["left_out"]) == (1, 0, 1)
    assert sha(unit1) == before
    saved = blocks(tmp_path / "word-lists" / "lily" / "z-words.md")
    assert [b["english"] for b in saved] == ["zealous"]


def test_update_rewrites_only_that_entry(tmp_path, ollama):
    unit1 = _with_unit1(tmp_path)
    original = blocks(unit1)
    client = _import_receive(tmp_path, ollama)
    client.post("/api/word-lists/import/choice", json={"index": 0, "choice": "update"})
    resp = client.post("/api/word-lists/import/confirm", json={})
    data = resp.get_json()
    assert (data["added"], data["updated"], data["left_out"]) == (1, 1, 0)

    receive, give_up = blocks(unit1)
    assert receive == {
        "english": "receive",
        "ipa": "rəˈsiːv",
        "alternates": [],
        "chinese": "接收；收到",
        "group": "unit1",
    }
    assert give_up == original[1]
    assert give_up["ipa"] == 42


def test_update_only_list_saves_no_new_file(tmp_path, ollama):
    _with_unit1(tmp_path)
    client = _import_receive(tmp_path, ollama, text="receive\n")
    client.post("/api/word-lists/import/choice", json={"index": 0, "choice": "update"})
    data = client.post("/api/word-lists/import/confirm", json={}).get_json()
    assert (data["added"], data["updated"]) == (0, 1)
    assert word_files(tmp_path) == ["unit1.md"]


def test_shared_match_is_included_and_shared_untouched(tmp_path, ollama):
    ollama.replies["river"] = {"chinese": "河",
                               "alternates": []}
    app = make_app(tmp_path)
    shared = tmp_path / "vocab" / "shared.md"
    before = sha(shared)
    client = login(app)
    start_import(client, "river\nzealous\n")
    finish(app, tmp_path)
    river = imported(client)["items"][0]
    assert river["existing"]["source"] == "shared"
    resp = client.post("/api/word-lists/import/choice", json={"index": 0, "choice": "update"})
    assert resp.status_code == 400

    data = client.post("/api/word-lists/import/confirm", json={}).get_json()
    assert data["added"] == 2
    saved = blocks(tmp_path / "word-lists" / "lily" / "z-words.md")
    assert [b["english"] for b in saved] == ["river", "zealous"]
    assert sha(shared) == before


def test_duplicate_words_in_upload(tmp_path, ollama):
    app = make_app(tmp_path)
    client = login(app)
    start_import(client, "zealous\ntyre\nZealous\n")
    finish(app, tmp_path)
    state = imported(client)
    assert state["total"] == 2
    assert state["items"][2]["state"] == "duplicate"
    assert state["items"][2]["duplicate_of"] == 0
    assert ollama.words.count("zealous") == 1
    data = client.post("/api/word-lists/import/confirm", json={}).get_json()
    assert (data["added"], data["left_out"]) == (2, 0)


# --- US4: pronunciations needing review ----------------------------------------


def test_review_items_are_saved_without_ipa(tmp_path, ollama):
    ollama.replies["record"] = {"chinese": "记录；唱片",
                                "alternates": []}
    app = make_app(tmp_path)
    client = login(app)
    start_import(client, "record\nzealous\n")
    finish(app, tmp_path)
    record = imported(client)["items"][0]
    assert record["ipa"] is None
    assert record["ipa_review"] == "pronunciation depends on the meaning"
    assert record["state"] == "enriched"

    client.post("/api/word-lists/import/confirm", json={})
    saved = blocks(tmp_path / "word-lists" / "lily" / "z-words.md")
    assert "ipa" not in saved[0]
    assert saved[1]["ipa"] == "ˈzeləs"

    client.post("/api/select", json={"collection": "z-words", "mode": "recall-only"})
    client.post("/api/answer", json={"answer": "record"})
    assert client.get("/api/state").get_json()["ipa"] is None
