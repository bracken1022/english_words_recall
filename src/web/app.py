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
from src.models.vocabulary_item import VocabularyItem, VocabularyItemError
from src.services.accounts import authenticate
from src.services.enrichment import (
    EnrichmentRunner,
    PendingImportStore,
    build_import,
    existing_lookup_for,
)
from src.services.speech_client import is_available, transcribe
from src.services.word_lists import (
    ListExistsError,
    UploadFormatError,
    WordListStore,
    parse_upload,
    sanitize_list_name,
)
from src.web.session_registry import SessionRegistry
from src.web.session_state import PracticeSession, WrongStepError

MAX_UPLOAD_BYTES = 1024 * 1024
MAX_SKIP_MESSAGES = 20
IMPORT_NO_WORDS = (
    "No words found. Put one English word per line — or upload a .md vocabulary file."
)


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
    word_lists_dir: Path | None = None,
) -> Flask:
    """*accounts* None keeps the original no-login, single-session web UI
    (only the pre-spec-015 tests rely on it); `python -m src.web` always
    passes the loaded account list (research.md R8). *word_lists_dir*
    (spec 016) enables per-account uploaded word lists; None means no
    uploads and every account practices from *vocab_dir*."""
    app = Flask(__name__)
    app.config["OLLAMA_URL"] = ollama_url
    app.config["MODEL"] = model
    app.config["VOICE_AVAILABLE"] = is_available()

    accounts_by_name: dict[str, Account] = {}
    store: WordListStore | None = None
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
        store = WordListStore(word_lists_dir) if word_lists_dir is not None else None
        app.session_registry = SessionRegistry(
            vocab_dir=vocab_dir,
            group=group,
            offer_choice=offer_choice,
            order=order,
            mode=mode,
            word_lists=store,
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

    if accounts is not None and store is not None:
        app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES

        @app.errorhandler(413)
        def too_large(_exc):
            return jsonify({"error": "The file is larger than 1 MB."}), 413

        @app.get("/api/word-lists")
        def get_word_lists():
            account = _current_account()
            return jsonify({"word_source": store.word_source(account), "lists": store.list(account)})

        @app.delete("/api/word-lists/<path:name>")
        def delete_word_list(name):
            account = _current_account()
            try:
                deleted = store.delete(account, name)
            except KeyError:
                return jsonify({"error": f'No list named "{name}".'}), 404
            app.session_registry.refresh_vocab(account)
            return jsonify({"deleted": deleted, "word_source": store.word_source(account)})

        @app.post("/api/word-lists")
        def post_word_list():
            upload = request.files.get("file")
            if upload is None or not upload.filename:
                return jsonify({"error": "Choose a file to upload."}), 400
            try:
                parsed = parse_upload(upload.filename, upload.read())
            except UploadFormatError as exc:
                status = 422 if str(exc).startswith("That list has") else 415
                return jsonify({"error": str(exc)}), status
            if not parsed.items:
                return jsonify(
                    {
                        "error": "No words found. Use one word per line, like: "
                        "receive, 收到 — or a .md vocabulary file.",
                        "skipped": parsed.skipped[:MAX_SKIP_MESSAGES],
                        "skipped_count": len(parsed.skipped),
                    }
                ), 422

            account = _current_account()
            name = sanitize_list_name(Path(upload.filename).stem)
            try:
                result = store.save(
                    account, name, parsed.items, replace=request.form.get("replace") == "true"
                )
            except ListExistsError as exc:
                return jsonify({"exists": True, "name": exc.name}), 409
            app.session_registry.refresh_vocab(account)
            return jsonify(
                {
                    "name": result.name,
                    "replaced": result.replaced,
                    "added": len(parsed.items),
                    "skipped_count": len(parsed.skipped),
                    "skipped": parsed.skipped[:MAX_SKIP_MESSAGES],
                    "first_list": result.first_list,
                    "applies_now": not _current_session().group_locked,
                }
            )

    if accounts is not None and store is not None:
        # Spec 018: uploads enriched by the local model, saved on confirm
        # (contracts/import-api-contract.md).
        runner = EnrichmentRunner(
            PendingImportStore(word_lists_dir), app.config["OLLAMA_URL"], app.config["MODEL"]
        )
        app.enrichment_runner = runner

        def _import_json(account: Account):
            return {"import": runner.state(account)}

        @app.get("/api/word-lists/import")
        def get_import():
            return jsonify(_import_json(_current_account()))

        @app.post("/api/word-lists/import")
        def post_import():
            upload = request.files.get("file")
            if upload is None or not upload.filename:
                return jsonify({"error": "Choose a file to upload."}), 400
            try:
                parsed = parse_upload(upload.filename, upload.read(), require_chinese=False)
            except UploadFormatError as exc:
                status = 422 if str(exc).startswith("That list has") else 415
                return jsonify({"error": str(exc)}), status
            if not parsed.items:
                return jsonify(
                    {
                        "error": IMPORT_NO_WORDS,
                        "skipped": parsed.skipped[:MAX_SKIP_MESSAGES],
                        "skipped_count": len(parsed.skipped),
                    }
                ), 422

            account = _current_account()
            if runner.get(account) is not None:
                if request.form.get("discard_pending") != "true":
                    return jsonify({"pending": True, **_import_json(account)}), 409
                runner.discard(account)
            name = sanitize_list_name(Path(upload.filename).stem)
            pending = build_import(
                name, upload.filename, parsed, existing_lookup_for(store, account, vocab_dir)
            )
            runner.begin(account, pending)
            return jsonify(_import_json(account)), 202

        @app.post("/api/word-lists/import/retry")
        def post_import_retry():
            account = _current_account()
            body = request.get_json(silent=True) or {}
            try:
                started = runner.retry(account, body.get("index"))
            except KeyError:
                return jsonify({"error": "Nothing to retry."}), 404
            except ValueError:
                return jsonify({"error": "That word can't be retried."}), 400
            # None: a batch is already running, so report it unchanged.
            return jsonify(_import_json(account)), 200 if started is None else 202

        @app.post("/api/word-lists/import/choice")
        def post_import_choice():
            account = _current_account()
            body = request.get_json(silent=True) or {}
            try:
                runner.set_choice(account, body.get("index"), body.get("choice"))
            except KeyError:
                return jsonify({"error": "Nothing to change."}), 404
            except ValueError:
                return jsonify({"error": "That word has no entry to update."}), 400
            return jsonify(_import_json(account))

        @app.post("/api/word-lists/import/confirm")
        def post_import_confirm():
            account = _current_account()
            body = request.get_json(silent=True) or {}
            with runner.lock(account):
                pending = runner.current(account)
                if pending is None:
                    return jsonify({"error": "Nothing to save."}), 404
                if runner.is_running(account) or pending.status == "running":
                    return jsonify({"error": "Still enriching — wait until it finishes."}), 409
                savable = pending.savable
                if not savable and not pending.updates:
                    return jsonify({"error": "No words are ready to save."}), 422
                try:
                    # Defence in depth: everything written must still be a
                    # valid vocabulary entry.
                    new_items = [
                        VocabularyItem(i.english, i.chinese, list(i.alternates), ipa=i.ipa)
                        for i in savable
                    ]
                except VocabularyItemError:
                    return jsonify({"error": "Couldn't save the list; nothing was changed."}), 500
                try:
                    result = store.apply_import(
                        account,
                        pending.list_name,
                        new_items,
                        updates=pending.update_map(),
                        replace=body.get("replace") is True,
                    )
                except ListExistsError as exc:
                    return jsonify({"exists": True, "name": exc.name}), 409
                except (OSError, KeyError):
                    return jsonify({"error": "Couldn't save the list; nothing was changed."}), 500
                left_out = pending.left_out_count
                updated = len(pending.updates)
                runner.forget(account)
            app.session_registry.refresh_vocab(account)
            return jsonify(
                {
                    "name": result.name,
                    "replaced": result.replaced,
                    "added": len(new_items),
                    "updated": updated,
                    "left_out": left_out,
                    "first_list": result.first_list,
                    "applies_now": not _current_session().group_locked,
                }
            )

        @app.delete("/api/word-lists/import")
        def delete_import():
            if not runner.discard(_current_account()):
                return jsonify({"error": "Nothing to discard."}), 404
            return jsonify({"discarded": True})

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/state")
    def get_state():
        state = {**_current_session().state(), "voice_available": app.config["VOICE_AVAILABLE"]}
        if accounts is not None:
            state["account"] = _account_json(_current_account())
            if store is not None:
                state["word_source"] = store.word_source(_current_account())
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
