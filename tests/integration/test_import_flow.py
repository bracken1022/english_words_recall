"""End-to-end flows for enriched uploads (spec 018 quickstart.md): upload
bare words, let the mocked local model enrich them, confirm, and practice
the saved list through the unchanged spec 016/017 paths."""

from src.services.vocabulary_loader import load_vocabulary
from tests.contract.test_import_api_contract import (  # noqa: F401 - fixture
    REPLIES,
    Gate,
    account,
    finish,
    imported,
    login,
    make_app,
    ollama,
    start_import,
)


def test_upload_enrich_confirm_practice(tmp_path, ollama):  # noqa: F811
    ollama.replies["tend to"] = {
        "chinese": "倾向于；往往会",
        "alternates": [],
    }
    app = make_app(tmp_path)
    client = login(app)
    assert start_import(client, "zealous\ntyre\nepitomise\ntend to\n").status_code == 202
    finish(app, tmp_path)

    items = {i["english"]: i for i in imported(client)["items"]}
    assert items["tyre"]["alternates"] == ["tire"]
    assert items["epitomise"]["alternates"] == ["epitomize"]
    assert items["tend to"]["ipa"] == "ˈtend tə"

    assert client.post("/api/word-lists/import/confirm", json={}).status_code == 200
    words, warnings = load_vocabulary(tmp_path / "word-lists" / "lily")
    assert len(words) == 4
    assert warnings == []

    client.post("/api/select", json={"collection": "z-words", "mode": "recall-only"})
    assert client.post("/api/answer", json={"answer": "zealous"}).get_json()["correct"] is True
    assert client.get("/api/state").get_json()["ipa"] == "ˈzeləs"


def test_restart_leaves_import_interrupted_and_resumable(tmp_path, ollama):  # noqa: F811
    gate = Gate(ollama, "tyre")
    first_app = make_app(tmp_path)
    client = login(first_app)
    start_import(client, "zealous\ntyre\nepitomise\n")
    assert gate.started.wait(5)
    # The old process dies mid-word: its worker never writes again.
    first_app.enrichment_runner.cancel(account(tmp_path))
    gate.release.set()
    first_app.enrichment_runner.wait(account(tmp_path), 5)

    ollama.replies["tyre"] = REPLIES["tyre"]
    second_app = make_app(tmp_path)
    client = login(second_app)
    state = imported(client)
    assert state["status"] == "interrupted"
    assert state["done"] == 1
    assert client.post("/api/word-lists/import/retry", json={}).status_code == 202
    finish(second_app, tmp_path)
    assert client.post("/api/word-lists/import/confirm", json={}).get_json()["added"] == 3


def test_imports_are_private_to_each_account(tmp_path, ollama):  # noqa: F811
    app = make_app(tmp_path)
    lily = login(app, "lily")
    weibo = login(app, "weibo")
    start_import(lily, "zealous\n")
    finish(app, tmp_path)
    pending_file = tmp_path / "word-lists" / "lily" / ".pending-import.json"
    before = pending_file.read_bytes()

    assert imported(weibo) is None
    assert weibo.post("/api/word-lists/import/retry", json={}).status_code == 404
    assert weibo.post("/api/word-lists/import/confirm", json={}).status_code == 404
    assert weibo.delete("/api/word-lists/import").status_code == 404
    assert pending_file.read_bytes() == before
    assert imported(lily)["items"][0]["english"] == "zealous"
