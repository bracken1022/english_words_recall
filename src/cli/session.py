"""The interactive recall session loop. After each answer the example
modes (spec 021) show the word's example sentence, made by the local
model on first practice and kept for next time."""

import dataclasses
import random
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from rich.console import Console

from src.cli.loading_indicator import run_with_indicator
from src.lib.ipa import display_ipa
from src.lib.pos import display_pos
from src.models.practice_attempt import PracticeAttempt
from src.models.vocabulary_item import VocabularyItem
from src.services.examples import ExampleService
from src.services.llm_client import DEFAULT_MODEL
from src.services.matcher import grade_answer
from src.services.progress_log import append_attempt
from src.services.vocabulary_loader import load_vocabulary

console = Console()

EXAMPLE_TIMEOUT = 6.0  # seconds to wait for a new example (spec 021, SC-001)


def _default_answer_input(prompt: str) -> str:
    return input(prompt)


def _wait_for_continue(prompt: str = "Press Enter to continue...") -> None:
    input(prompt)


def run_recall_step(
    item: VocabularyItem,
    answer_input: Callable[[], str] | None = None,
    examples=None,
) -> PracticeAttempt:
    """Show the Chinese meaning, collect an answer, grade it, reveal the result.

    FR-002 (hide English until submission), FR-003 (free-text answer),
    FR-004 (exact-match grading), FR-005 (always reveal after submission).
    """
    labels = f"{display_pos(item.pos)} " if item.pos else ""
    console.print(f"Chinese meaning: {labels}[bold]{item.chinese}[/bold]")

    if answer_input is None:
        answer = _default_answer_input("Your answer (English): ")
    else:
        answer = answer_input()

    correct = grade_answer(item, answer)
    accepted = ", ".join(item.accepted_expressions())

    if correct:
        console.print(f"[green]Correct![/green] Accepted expression(s): {accepted}")
    else:
        console.print(f"[red]Incorrect.[/red] The correct expression(s): {accepted}")
    if item.ipa:
        console.print(f"Pronunciation: {display_ipa(item.ipa)}")
    if examples is not None:
        show_example(item, examples)

    return PracticeAttempt(
        timestamp=datetime.now(UTC).isoformat(timespec="seconds"),
        item=item.english,
        answer=answer,
        correct=correct,
    )


def show_example(item: VocabularyItem, examples) -> dict | None:
    """Print the word's example sentence, making it first if needed."""
    example = run_with_indicator(
        console, "Writing an example...", examples.get_or_make, item, EXAMPLE_TIMEOUT
    )
    if example:
        console.print(f"Example: {example['sentence']}")
        console.print(f"         {example['translation']}")
    else:
        console.print("(No example right now.)")
    return example


def run_sentence_recall(example: dict) -> str | None:
    """Self-checked sentence recall (spec 021 US2, contracts/cli.md):
    show the translation, let the learner try the sentence, reveal it,
    and return "got" or "not_yet" — or None if they skip."""
    console.print(f"Recall the sentence: {example['translation']}")
    if input("Press Enter to show it (s to skip) ").strip().lower() == "s":
        return None
    console.print(f"Example: {example['sentence']}")
    while True:
        reply = input("Did you get it? [y/n] ").strip().lower()
        if reply in ("y", "yes"):
            return "got"
        if reply in ("n", "no"):
            return "not_yet"


def run_session(
    vocab_dir: Path,
    progress_file: Path,
    group: str | None = None,
    ollama_url: str = "http://localhost:11434",
    model: str = DEFAULT_MODEL,
    order: str = "sequential",
    mode: str = "example",
) -> None:
    """Run a full practice session: load items, filter, then walk forward
    through the recall step for each one, one at a time, no skip/back
    (FR-015, FR-016). *order* ("sequential" [default] or "random", spec
    011) shuffles the filtered pool once, before the walk begins. *mode*
    (spec 021: "recall-only", "example" [default] or "example-recall";
    "sentence" means "example") decides whether each answer is followed
    by the word's example sentence, and, in "example-recall", by a
    self-checked recall of that sentence."""
    if mode not in ("recall-only", "example", "example-recall"):
        mode = "example"
    examples = None
    if mode != "recall-only":
        examples = ExampleService(None, ollama_url, model).bind(None)
    items, warnings = load_vocabulary(vocab_dir)
    for warning in warnings:
        console.print(f"[yellow]Warning:[/yellow] {warning}")

    if group is not None:
        items = [item for item in items if item.group == group]

    if order == "random":
        random.shuffle(items)

    if not items:
        console.print("No vocabulary items available for this session.")
        return

    for item in items:
        attempt = run_recall_step(item, examples=examples)
        if mode != "recall-only" or not attempt.correct:
            # Wait for an explicit continue before moving on (spec 013),
            # so the answer and its example can be read.
            _wait_for_continue()
        if mode == "example-recall":
            example = examples.get(item)
            if example:
                print()
                mark = run_sentence_recall(example)
                attempt = dataclasses.replace(attempt, sentence_recall=mark)
        append_attempt(progress_file, attempt)
        print()
