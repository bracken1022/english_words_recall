"""CLI entry point for the web UI: `python -m src.web`."""

import argparse
import sys
from pathlib import Path

from src.services.accounts import AccountsFileError, load_accounts
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
        "--order",
        choices=["sequential", "random"],
        default="sequential",
        help=(
            "Order to present words in (default: sequential). Only takes effect "
            "when --group is also given; otherwise the interactive choose screen "
            "governs order."
        ),
    )
    parser.add_argument(
        "--mode",
        choices=["sentence", "recall-only"],
        default="sentence",
        help=(
            "Practice mode: sentence-writing or recall only (default: sentence). "
            "Only takes effect when --group is also given; otherwise the "
            "interactive choose screen governs mode."
        ),
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Bind address (default: 0.0.0.0, reachable from other devices on the local network)",
    )
    parser.add_argument("--port", type=int, default=8420)
    parser.add_argument(
        "--accounts-file",
        type=Path,
        default=Path("accounts.yml"),
        help=(
            "Learner accounts allowed to log in (default: accounts.yml; "
            "copy accounts.example.yml to start)"
        ),
    )
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    try:
        accounts = load_accounts(args.accounts_file, args.progress_file)
    except AccountsFileError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)
    app = create_app(
        vocab_dir=args.vocab_dir,
        progress_file=args.progress_file,
        group=args.group,
        ollama_url=args.ollama_url,
        model=args.model,
        offer_choice=args.group is None,
        order=args.order,
        mode=args.mode,
        accounts=accounts,
    )
    print(f"English Tutor web UI running at http://{args.host}:{args.port} (Ctrl+C to stop)")
    print("Accounts: " + ", ".join(f"{a.username} → {a.progress_file}" for a in accounts))
    # Explicitly threaded so one account's slow sentence review never blocks
    # another account's requests (spec 015, research.md R3).
    app.run(host=args.host, port=args.port, threaded=True)


if __name__ == "__main__":
    main()
