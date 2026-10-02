"""Contract tests for contracts/word-lists-api-contract.md (spec 016)."""

import io
from pathlib import Path

import pytest

from src.models.account import Account
from src.web.app import create_app

SHARED = "---\nenglish: river\nchinese: 河\ngroup: shared-set\n---\n"
UNIT1 = "English, Chinese\nreceive, 收到\nbroken line\n"


def _make_app(tmp_path: Path, with_store: bool = True, with_accounts: bool = True):
    vocab_dir = tmp_path / "vocab"
    vocab_dir.mkdir()
    (vocab_dir / "shared.md").write_text(SHARED, encoding="utf-8")
    kwargs = {}
    if with_accounts:
        kwargs["accounts"] = [
            Account("weibo", "pw-weibo", "Weibo", tmp_path / "progress.md"),
            Account("lily", "pw-lily", "Lily", tmp_path / "progress-lily.md"),
        ]
    if with_store:
        kwargs["word_lists_dir"] = tmp_path / "word-lists"
    return create_app(
        vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md", offer_choice=True, **kwargs
    )


def _client(tmp_path: Path, username: str | None = "lily", **kwargs):
    client = _make_app(tmp_path, **kwargs).test_client()
    if username:
        resp = client.post("/api/login", json={"username": username, "password": f"pw-{username}"})
        assert resp.status_code == 200
    return client


def upload(client, text, filename="unit1.csv", replace=None, raw: bytes | None = None):
    data = {"file": (io.BytesIO(raw if raw is not None else text.encode("utf-8")), filename)}
    if replace is not None:
        data["replace"] = replace
    return client.post("/api/word-lists", data=data, content_type="multipart/form-data")


# --- POST /api/word-lists (US1) ----------------------------------------------


def test_upload_requires_login(tmp_path: Path):
    client = _client(tmp_path, username=None)
    resp = upload(client, UNIT1)
    assert resp.status_code == 401
    assert resp.get_json() == {"error": "login required"}
    assert not (tmp_path / "word-lists").exists()


def test_missing_file_part(tmp_path: Path):
    client = _client(tmp_path)
    resp = client.post("/api/word-lists", data={}, content_type="multipart/form-data")
    assert resp.status_code == 400
    assert resp.get_json() == {"error": "Choose a file to upload."}


def test_empty_filename(tmp_path: Path):
    client = _client(tmp_path)
    resp = upload(client, UNIT1, filename="")
    assert resp.status_code == 400


def test_unsupported_type(tmp_path: Path):
    client = _client(tmp_path)
    resp = upload(client, "x", filename="x.xlsx")
    assert resp.status_code == 415
    assert resp.get_json() == {
        "error": 'Unsupported file type ".xlsx". Upload a .csv, .txt or .md file.'
    }


def test_no_words_is_422_and_nothing_saved(tmp_path: Path):
    client = _client(tmp_path)
    resp = upload(client, "\n\n", filename="blank.txt")
    assert resp.status_code == 422
    assert resp.get_json()["error"].startswith("No words found.")
    assert not (tmp_path / "word-lists" / "lily").exists()


def test_too_many_words_is_422(tmp_path: Path):
    client = _client(tmp_path)
    text = "".join(f"w{i}, 词\n" for i in range(5001))
    resp = upload(client, text)
    assert resp.status_code == 422
    assert resp.get_json() == {"error": "That list has 5001 words; the limit is 5,000."}


def test_too_large_is_json_413(tmp_path: Path):
    client = _client(tmp_path)
    resp = upload(client, None, raw=b"a, b\n" * 220000)
    assert resp.status_code == 413
    assert resp.get_json() == {"error": "The file is larger than 1 MB."}


def test_successful_upload_result(tmp_path: Path):
    client = _client(tmp_path)
    resp = upload(client, UNIT1)
    assert resp.status_code == 200
    assert resp.get_json() == {
        "name": "unit1",
        "replaced": False,
        "added": 1,
        "skipped_count": 1,
        "skipped": ["line 3: no Chinese meaning"],
        "first_list": True,
        "applies_now": True,
    }
    assert (tmp_path / "word-lists" / "lily" / "unit1.md").exists()


def test_skip_messages_capped_at_20(tmp_path: Path):
    client = _client(tmp_path)
    resp = upload(client, "receive, 收到\n" + "broken\n" * 25)
    data = resp.get_json()
    assert data["skipped_count"] == 25
    assert len(data["skipped"]) == 20


def test_existing_name_needs_confirmation(tmp_path: Path):
    client = _client(tmp_path)
    upload(client, UNIT1)
    path = tmp_path / "word-lists" / "lily" / "unit1.md"
    before = path.read_text(encoding="utf-8")
    resp = upload(client, "give up, 放弃", filename="Unit1.csv")
    assert resp.status_code == 409
    assert resp.get_json() == {"exists": True, "name": "unit1"}
    assert path.read_text(encoding="utf-8") == before


@pytest.mark.parametrize("with_accounts", [True, False])
def test_no_word_list_routes_without_a_store(tmp_path: Path, with_accounts):
    username = "lily" if with_accounts else None
    client = _client(tmp_path, username=username, with_store=False, with_accounts=with_accounts)
    assert upload(client, UNIT1).status_code == 404


# --- GET /api/state word_source (US2) -----------------------------------------


def test_state_reports_word_source(tmp_path: Path):
    client = _client(tmp_path)
    assert client.get("/api/state").get_json()["word_source"] == "shared"
    upload(client, UNIT1)
    assert client.get("/api/state").get_json()["word_source"] == "own"


def test_state_has_no_word_source_without_store(tmp_path: Path):
    client = _client(tmp_path, with_store=False)
    assert "word_source" not in client.get("/api/state").get_json()


def test_state_never_mentions_another_accounts_lists(tmp_path: Path):
    app = _make_app(tmp_path)
    lily = app.test_client()
    lily.post("/api/login", json={"username": "lily", "password": "pw-lily"})
    upload(lily, "secretword, 秘密\n", filename="lilys-list.csv")
    weibo = app.test_client()
    weibo.post("/api/login", json={"username": "weibo", "password": "pw-weibo"})
    body = weibo.get("/api/state").get_data(as_text=True)
    assert "lilys-list" not in body
    assert "secretword" not in body


# --- GET/DELETE /api/word-lists and replace (US3) ------------------------------


def test_get_word_lists(tmp_path: Path):
    client = _client(tmp_path)
    assert client.get("/api/word-lists").get_json() == {"word_source": "shared", "lists": []}
    upload(client, "x, 词", filename="b.csv")
    upload(client, "y, 词\nz, 词", filename="A.csv")
    data = client.get("/api/word-lists").get_json()
    assert data["word_source"] == "own"
    assert [(e["name"], e["word_count"]) for e in data["lists"]] == [("A", 2), ("b", 1)]
    assert all("uploaded_at" in e for e in data["lists"])


def test_replace_true_overwrites(tmp_path: Path):
    client = _client(tmp_path)
    upload(client, UNIT1)
    resp = upload(client, "give up, 放弃\nlook up, 查找", filename="unit1.csv", replace="true")
    assert resp.status_code == 200
    data = resp.get_json()
    assert (data["replaced"], data["first_list"], data["added"]) == (True, False, 2)
    text = (tmp_path / "word-lists" / "lily" / "unit1.md").read_text(encoding="utf-8")
    assert "receive" not in text and "give up" in text


def test_delete_word_list(tmp_path: Path):
    client = _client(tmp_path)
    upload(client, UNIT1)
    resp = client.delete("/api/word-lists/unit1")
    assert resp.status_code == 200
    assert resp.get_json() == {"deleted": "unit1", "word_source": "shared"}
    again = client.delete("/api/word-lists/unit1")
    assert again.status_code == 404
    assert again.get_json() == {"error": 'No list named "unit1".'}


def test_delete_cannot_touch_another_account(tmp_path: Path):
    app = _make_app(tmp_path)
    lily = app.test_client()
    lily.post("/api/login", json={"username": "lily", "password": "pw-lily"})
    upload(lily, UNIT1)
    weibo = app.test_client()
    weibo.post("/api/login", json={"username": "weibo", "password": "pw-weibo"})
    assert weibo.delete("/api/word-lists/unit1").status_code == 404
    assert weibo.delete("/api/word-lists/..%2Flily%2Funit1").status_code == 404
    assert weibo.delete("/api/word-lists/../lily/unit1").status_code == 404
    assert (tmp_path / "word-lists" / "lily" / "unit1.md").exists()


def test_list_and_delete_require_login(tmp_path: Path):
    client = _client(tmp_path, username=None)
    assert client.get("/api/word-lists").status_code == 401
    assert client.delete("/api/word-lists/unit1").status_code == 401
