"""CLI entry point for the vocabulary recall tutor."""

import argparse
from pathlib import Path

from src.cli.session import run_session
from src.services.llm_client import DEFAULT_MODEL


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="english-tutor",
        description="Local English vocabulary recall tutor for Chinese speakers.",
    )
    parser.add_argument(
        "--vocab-dir",
        type=Path,
        default=Path("vocabulary"),
        help="Directory containing vocabulary Markdown files (default: ./vocabulary)",
    )
    parser.add_argument(
        "--progress-file",
        type=Path,
        default=Path("progress.md"),
        help="Path to the progress log Markdown file (default: ./progress.md)",
    )
    parser.add_argument(
        "--group",
        default=None,
        help="Only practice vocabulary items tagged with this group/lesson (default: all items)",
    )
    parser.add_argument(
        "--ollama-url",
        default="http://localhost:11434",
        help="Base URL of the local Ollama server (default: http://localhost:11434)",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Name of the local Ollama model that writes example sentences (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--order",
        choices=["sequential", "random"],
        default="sequential",
        help="Order to present words in (default: sequential)",
    )
    parser.add_argument(
        "--mode",
        choices=["recall-only", "example", "example-recall", "sentence"],
        default="example",
        help=(
            "Practice mode: recall only, recall + example sentence, or recall + example + "
            "sentence recall (default: example; 'sentence' is accepted as 'example')"
        ),
    )
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    run_session(
        vocab_dir=args.vocab_dir,
        progress_file=args.progress_file,
        group=args.group,
        ollama_url=args.ollama_url,
        model=args.model,
        order=args.order,
        mode=args.mode,
    )


if __name__ == "__main__":
    main()
