"""Contract tests for contracts/web-auth-api-contract.md (spec 015)."""

from pathlib import Path

import pytest

from src.models.account import Account
from src.web.app import create_app

VOCAB = "---\nenglish: receive\nchinese: 收到\n---\n"


def _accounts(tmp_path: Path) -> list[Account]:
    return [
        Account("weibo", "change-me", "Weibo", tmp_path / "progress.md"),
        Account("lily", "lily-pw", None, tmp_path / "progress-lily.md"),
    ]


def _make_app(tmp_path: Path, accounts="default"):
    vocab_dir = tmp_path / "vocab"
    vocab_dir.mkdir()
    (vocab_dir / "unit1.md").write_text(VOCAB, encoding="utf-8")
    kwargs = {}
    if accounts == "default":
        kwargs["accounts"] = _accounts(tmp_path)
    return create_app(
        vocab_dir=vocab_dir,
        progress_file=tmp_path / "progress.md",
        offer_choice=True,
        **kwargs,
    )


def _login(client, username="weibo", password="change-me"):
    return client.post("/api/login", json={"username": username, "password": password})


# --- POST /api/login ---------------------------------------------------------


def test_login_success_returns_account_without_password(tmp_path: Path):
    client = _make_app(tmp_path).test_client()
    resp = _login(client, "Weibo ", "change-me")
    assert resp.status_code == 200
    assert resp.get_json() == {"account": {"username": "weibo", "display_name": "Weibo"}}
    assert b"change-me" not in resp.data


def test_wrong_password_and_unknown_user_get_identical_401(tmp_path: Path):
    client = _make_app(tmp_path).test_client()
    wrong_pw = _login(client, "weibo", "nope")
    unknown = _login(client, "nobody", "change-me")
    assert wrong_pw.status_code == unknown.status_code == 401
    assert (
        wrong_pw.get_json() == unknown.get_json() == {"error": "Username or password is incorrect"}
    )
    assert client.get("/api/state").status_code == 401


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"username": "weibo"},
        {"password": "change-me"},
        {"username": 1, "password": "change-me"},
        {"username": "weibo", "password": None},
        {"username": "  ", "password": "change-me"},
        {"username": "weibo", "password": ""},
    ],
)
def test_missing_or_empty_fields_get_400(tmp_path: Path, body):
    client = _make_app(tmp_path).test_client()
    resp = client.post("/api/login", json=body)
    assert resp.status_code == 400
    assert resp.get_json() == {"error": "Enter both a username and a password"}


# --- guard -------------------------------------------------------------------

GUARDED = [
    ("get", "/api/state"),
    ("post", "/api/answer"),
    ("post", "/api/sentence"),
    ("post", "/api/select"),
    ("post", "/api/skip"),
    ("post", "/api/restart"),
    ("post", "/api/end"),
    ("post", "/api/retry-sentence"),
    ("post", "/api/continue"),
    ("post", "/api/transcribe"),
    ("post", "/api/logout"),
]


@pytest.mark.parametrize(("method", "path"), GUARDED)
def test_every_api_route_requires_login(tmp_path: Path, method, path):
    client = _make_app(tmp_path).test_client()
    resp = getattr(client, method)(path, json={"answer": "receive", "collection": None})
    assert resp.status_code == 401
    assert resp.get_json() == {"error": "login required"}
    assert not (tmp_path / "progress.md").exists()
    assert not (tmp_path / "progress-lily.md").exists()


def test_page_itself_is_served_without_login(tmp_path: Path):
    client = _make_app(tmp_path).test_client()
    assert client.get("/").status_code == 200


def test_cookie_with_unknown_login_is_rejected(tmp_path: Path):
    client = _make_app(tmp_path).test_client()
    with client.session_transaction() as sess:
        sess["login_id"] = "forged"
        sess["username"] = "weibo"
    assert client.get("/api/state").status_code == 401


# --- GET /api/state ----------------------------------------------------------


def test_state_includes_account_after_login(tmp_path: Path):
    client = _make_app(tmp_path).test_client()
    _login(client)
    resp = client.get("/api/state")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["step"] == "choose"
    assert data["account"] == {"username": "weibo", "display_name": "Weibo"}


def test_state_account_display_name_null_when_unset(tmp_path: Path):
    client = _make_app(tmp_path).test_client()
    _login(client, "lily", "lily-pw")
    assert client.get("/api/state").get_json()["account"] == {
        "username": "lily",
        "display_name": None,
    }


def test_legacy_app_without_accounts_needs_no_login(tmp_path: Path):
    client = _make_app(tmp_path, accounts=None).test_client()
    resp = client.get("/api/state")
    assert resp.status_code == 200
    assert "account" not in resp.get_json()


# --- POST /api/logout and the login cookie (US3) ---------------------------


def test_logout_ends_access(tmp_path: Path):
    client = _make_app(tmp_path).test_client()
    _login(client)
    resp = client.post("/api/logout")
    assert resp.status_code == 200
    assert resp.get_json() == {"ok": True}
    assert client.get("/api/state").status_code == 401


def test_logout_without_login_is_401(tmp_path: Path):
    client = _make_app(tmp_path).test_client()
    assert client.post("/api/logout").status_code == 401


def test_login_cookie_is_persistent_httponly_lax_and_holds_no_password(tmp_path: Path):
    client = _make_app(tmp_path).test_client()
    resp = _login(client)
    cookie = resp.headers["Set-Cookie"]
    assert "Expires=" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie
    assert "change-me" not in cookie


def test_logging_in_again_switches_account(tmp_path: Path):
    client = _make_app(tmp_path).test_client()
    _login(client)
    _login(client, "lily", "lily-pw")
    assert client.get("/api/state").get_json()["account"]["username"] == "lily"


def test_cookie_saved_before_logout_no_longer_works(tmp_path: Path):
    app = _make_app(tmp_path)
    client = app.test_client()
    _login(client)
    with client.session_transaction() as sess:
        saved = dict(sess)
    client.post("/api/logout")

    replay = app.test_client()
    with replay.session_transaction() as sess:
        sess.update(saved)
    assert replay.get("/api/state").status_code == 401
