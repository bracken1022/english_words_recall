"""Flask app factory for the web UI (spec 003). Owns one shared
PracticeSession per running server process (see research.md "Session/state
model")."""

from pathlib import Path

from flask import Flask, jsonify, render_template, request

from src.services.speech_client import is_available, transcribe
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
) -> Flask:
    app = Flask(__name__)
    session = PracticeSession(
        vocab_dir=vocab_dir,
        progress_file=progress_file,
        group=group,
        offer_choice=offer_choice,
        order=order,
        mode=mode,
    )
    app.config["OLLAMA_URL"] = ollama_url
    app.config["MODEL"] = model
    app.config["VOICE_AVAILABLE"] = is_available()
    app.practice_session = session

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/state")
    def get_state():
        return jsonify({**session.state(), "voice_available": app.config["VOICE_AVAILABLE"]})

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
            result = session.submit_answer(body["answer"])
        except WrongStepError as exc:
            return jsonify({"error": str(exc)}), 409
        return jsonify(result)

    @app.post("/api/sentence")
    def post_sentence():
        body = request.get_json(silent=True) or {}
        if "sentence" not in body:
            return jsonify({"error": "missing 'sentence'"}), 400
        try:
            result = session.submit_sentence(
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
            session.select_collection(body["collection"], order=select_order, mode=select_mode)
        except WrongStepError as exc:
            return jsonify({"error": str(exc)}), 409
        return jsonify(session.state())

    @app.post("/api/skip")
    def post_skip():
        try:
            session.skip_sentence()
        except WrongStepError as exc:
            return jsonify({"error": str(exc)}), 409
        return jsonify(session.state())

    @app.post("/api/restart")
    def post_restart():
        try:
            session.restart()
        except WrongStepError as exc:
            return jsonify({"error": str(exc)}), 409
        return jsonify(session.state())

    @app.post("/api/continue")
    def post_continue():
        try:
            session.continue_to_next()
        except WrongStepError as exc:
            return jsonify({"error": str(exc)}), 409
        return jsonify(session.state())

    return app
