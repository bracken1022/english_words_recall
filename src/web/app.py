"""Flask app factory for the web UI (spec 003). Without accounts it owns
one shared PracticeSession per running server process (see research.md
"Session/state model"); with accounts (spec 015) every /api/* call needs a
login and acts on that account's own PracticeSession and progress file."""

import secrets
from datetime import timedelta
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from flask import session as login_session

from src.models.account import Account
from src.services.accounts import authenticate
from src.services.speech_client import is_available, transcribe
from src.web.session_registry import SessionRegistry
from src.web.session_state import PracticeSession, WrongStepError


def create_app(
    vocab_dir: Path,
    progress_file: Path,
    group: str | None = None,
    ollama_url: str = "http://localhost:11434",
    model: str = "qwen3:14b",
    offer_choice: bool = False,
    order: str = "sequential",
    mode: str = "sentence",
    accounts: list[Account] | None = None,
) -> Flask:
    """*accounts* None keeps the original no-login, single-session web UI
    (only the pre-spec-015 tests rely on it); `python -m src.web` always
    passes the loaded account list (research.md R8)."""
    app = Flask(__name__)
    app.config["OLLAMA_URL"] = ollama_url
    app.config["MODEL"] = model
    app.config["VOICE_AVAILABLE"] = is_available()

    accounts_by_name: dict[str, Account] = {}
    if accounts is None:
        app.practice_session = PracticeSession(
            vocab_dir=vocab_dir,
            progress_file=progress_file,
            group=group,
            offer_choice=offer_choice,
            order=order,
            mode=mode,
        )
    else:
        # A fresh key per process: restarting the server logs everyone out.
        app.secret_key = secrets.token_hex(32)
        app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
        app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=365)
        accounts_by_name = {account.username: account for account in accounts}
        # Live logins: random login id (kept in the cookie) -> username.
        # Logout deletes the id, so a copy of the old cookie stops working.
        active_logins: dict[str, str] = {}
        app.session_registry = SessionRegistry(
            vocab_dir=vocab_dir, group=group, offer_choice=offer_choice, order=order, mode=mode
        )

        @app.before_request
        def require_login():
            if not request.path.startswith("/api/") or request.path == "/api/login":
                return None
            if active_logins.get(login_session.get("login_id")) not in accounts_by_name:
                return jsonify({"error": "login required"}), 401
            return None

        @app.post("/api/login")
        def post_login():
            body = request.get_json(silent=True) or {}
            username = body.get("username")
            password = body.get("password")
            if (
                not isinstance(username, str)
                or not isinstance(password, str)
                or not username.strip()
                or password == ""
            ):
                return jsonify({"error": "Enter both a username and a password"}), 400
            account = authenticate(accounts, username, password)
            if account is None:
                return jsonify({"error": "Username or password is incorrect"}), 401
            # Permanent: the login survives browser restarts (FR-010) until
            # logout or a server restart.
            login_session.clear()
            login_session.permanent = True
            login_id = secrets.token_urlsafe(32)
            active_logins[login_id] = account.username
            login_session["login_id"] = login_id
            return jsonify({"account": _account_json(account)})

        @app.post("/api/logout")
        def post_logout():
            # Starting the account over discards any word in progress
            # without recording it (FR-009, research.md R7).
            app.session_registry.reset(_current_account())
            active_logins.pop(login_session.get("login_id"), None)
            login_session.clear()
            return jsonify({"ok": True})

    def _current_account() -> Account:
        return accounts_by_name[active_logins[login_session["login_id"]]]

    def _current_session() -> PracticeSession:
        if accounts is None:
            return app.practice_session
        return app.session_registry.get(_current_account())

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/state")
    def get_state():
        state = {**_current_session().state(), "voice_available": app.config["VOICE_AVAILABLE"]}
        if accounts is not None:
            state["account"] = _account_json(_current_account())
        return jsonify(state)

    @app.post("/api/transcribe")
    def post_transcribe():
        result = transcribe(request.get_data(), content_type=request.content_type or "")
        return jsonify({"available": result.available, "text": result.text})

    @app.post("/api/answer")
    def post_answer():
        body = request.get_json(silent=True) or {}
        if "answer" not in body:
            return jsonify({"error": "missing 'answer'"}), 400
        try:
            result = _current_session().submit_answer(body["answer"])
        except WrongStepError as exc:
            return jsonify({"error": str(exc)}), 409
        return jsonify(result)

    @app.post("/api/sentence")
    def post_sentence():
        body = request.get_json(silent=True) or {}
        if "sentence" not in body:
            return jsonify({"error": "missing 'sentence'"}), 400
        try:
            result = _current_session().submit_sentence(
                body["sentence"],
                base_url=app.config["OLLAMA_URL"],
                model=app.config["MODEL"],
            )
        except WrongStepError as exc:
            return jsonify({"error": str(exc)}), 409
        return jsonify(result)

    @app.post("/api/select")
    def post_select():
        body = request.get_json(silent=True) or {}
        if "collection" not in body:
            return jsonify({"error": "missing 'collection'"}), 400
        select_order = body.get("order")
        if select_order not in ("sequential", "random"):
            select_order = "sequential"
        select_mode = body.get("mode")
        if select_mode not in ("sentence", "recall-only"):
            select_mode = "sentence"
        try:
            _current_session().select_collection(body["collection"], order=select_order, mode=select_mode)
        except WrongStepError as exc:
            return jsonify({"error": str(exc)}), 409
        return jsonify(_current_session().state())

    @app.post("/api/skip")
    def post_skip():
        try:
            _current_session().skip_sentence()
        except WrongStepError as exc:
            return jsonify({"error": str(exc)}), 409
        return jsonify(_current_session().state())

    @app.post("/api/restart")
    def post_restart():
        try:
            _current_session().restart()
        except WrongStepError as exc:
            return jsonify({"error": str(exc)}), 409
        return jsonify(_current_session().state())

    @app.post("/api/end")
    def post_end():
        try:
            _current_session().end_session()
        except WrongStepError as exc:
            return jsonify({"error": str(exc)}), 409
        return jsonify(_current_session().state())

    @app.post("/api/retry-sentence")
    def post_retry_sentence():
        try:
            _current_session().retry_sentence()
        except WrongStepError as exc:
            return jsonify({"error": str(exc)}), 409
        return jsonify(_current_session().state())

    @app.post("/api/continue")
    def post_continue():
        try:
            _current_session().continue_to_next()
        except WrongStepError as exc:
            return jsonify({"error": str(exc)}), 409
        return jsonify(_current_session().state())

    return app


def _account_json(account: Account) -> dict:
    return {"username": account.username, "display_name": account.display_name}
