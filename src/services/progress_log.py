"""Append-only Markdown progress log of PracticeAttempts (FR-011,
contracts/progress-log-format.md)."""

from pathlib import Path

import yaml

from src.lib.markdown_blocks import parse_blocks
from src.models.practice_attempt import PracticeAttempt, PracticeAttemptError


def append_attempt(progress_file: Path, attempt: PracticeAttempt) -> None:
    """Append *attempt* to *progress_file* as a new '---'-delimited YAML block."""
    block: dict = {
        "timestamp": attempt.timestamp,
        "item": attempt.item,
        "answer": attempt.answer,
        "correct": attempt.correct,
    }
    if attempt.sentence is not None:
        block["sentence"] = attempt.sentence
        block["feedback"] = attempt.feedback
    if attempt.sentence_recall is not None:
        block["sentence_recall"] = attempt.sentence_recall

    yaml_text = yaml.safe_dump(block, allow_unicode=True, sort_keys=False, default_flow_style=False)

    with progress_file.open("a", encoding="utf-8") as f:
        f.write(f"\n---\n{yaml_text}---\n")


def read_attempts(progress_file: Path) -> tuple[list[PracticeAttempt], list[str]]:
    """Read all PracticeAttempts from *progress_file*.

    Returns (attempts, warnings); a block that fails to parse or is missing
    a required field is skipped and reported, without blocking the rest of
    the log from being read.
    """
    if not progress_file.exists():
        return [], []

    text = progress_file.read_text(encoding="utf-8")
    blocks, warnings = parse_blocks(text)

    attempts: list[PracticeAttempt] = []
    for block in blocks:
        try:
            attempts.append(PracticeAttempt.from_block(block))
        except PracticeAttemptError as exc:
            warnings.append(str(exc))

    return attempts, warnings
