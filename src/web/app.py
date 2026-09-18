"""Flask app factory for the web UI (spec 003). Owns one shared
PracticeSession per running server process (see research.md "Session/state
model")."""

from pathlib import Path

from flask import Flask, jsonify, render_template, request

from src.web.session_state import PracticeSession, WrongStepError


def create_app(
    vocab_dir: Path,
    progress_file: Path,
    group: str | None = None,
    ollama_url: str = "http://localhost:11434",
    model: str = "qwen3:14b",
) -> Flask:
    app = Flask(__name__)
    session = PracticeSession(vocab_dir=vocab_dir, progress_file=progress_file, group=group)
    app.config["OLLAMA_URL"] = ollama_url
    app.config["MODEL"] = model
    app.practice_session = session

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/state")
    def get_state():
        return jsonify(session.state())

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

    @app.post("/api/continue")
    def post_continue():
        try:
            session.continue_to_next()
        except WrongStepError as exc:
            return jsonify({"error": str(exc)}), 409
        return jsonify(session.state())

    return app
