"""CLI entry point for the web UI: `python -m src.web`."""

import argparse
from pathlib import Path

from src.services.llm_client import DEFAULT_MODEL
from src.web.app import create_app


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="english-tutor-web",
        description="Local English vocabulary recall tutor — web UI (LAN-reachable).",
    )
    parser.add_argument("--vocab-dir", type=Path, default=Path("vocabulary"))
    parser.add_argument("--progress-file", type=Path, default=Path("progress.md"))
    parser.add_argument("--group", default=None)
    parser.add_argument("--ollama-url", default="http://localhost:11434")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Bind address (default: 0.0.0.0, reachable from other devices on the local network)",
    )
    parser.add_argument("--port", type=int, default=8420)
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    app = create_app(
        vocab_dir=args.vocab_dir,
        progress_file=args.progress_file,
        group=args.group,
        ollama_url=args.ollama_url,
        model=args.model,
        offer_choice=args.group is None,
    )
    print(f"English Tutor web UI running at http://{args.host}:{args.port} (Ctrl+C to stop)")
    app.run(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
