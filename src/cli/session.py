"""The interactive recall -> sentence -> correction session loop."""

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from rich.console import Console

from src.models.practice_attempt import PracticeAttempt
from src.models.vocabulary_item import VocabularyItem
from src.services.llm_client import DEFAULT_MODEL, request_correction
from src.services.matcher import grade_answer
from src.services.progress_log import append_attempt
from src.services.vocabulary_loader import load_vocabulary

console = Console()


def _default_answer_input(prompt: str) -> str:
    return input(prompt)


def run_recall_step(
    item: VocabularyItem,
    answer_input: Callable[[], str] | None = None,
) -> PracticeAttempt:
    """Show the Chinese meaning, collect an answer, grade it, reveal the result.

    FR-002 (hide English until submission), FR-003 (free-text answer),
    FR-004 (exact-match grading), FR-005 (always reveal after submission).
    """
    console.print(f"Chinese meaning: [bold]{item.chinese}[/bold]")

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

    return PracticeAttempt(
        timestamp=datetime.now(UTC).isoformat(timespec="seconds"),
        item=item.english,
        answer=answer,
        correct=correct,
    )


def run_sentence_step(
    target_expression: str,
    sentence_input: Callable[[], str] | None = None,
    base_url: str = "http://localhost:11434",
    model: str = DEFAULT_MODEL,
) -> tuple[str, str]:
    """Prompt for a sentence using *target_expression* and show correction
    feedback from the local LLM. Returns (sentence, feedback_summary), where
    feedback_summary is a short string suitable for the progress log
    (FR-006, FR-008, FR-009, FR-010)."""
    console.print(f'Write a sentence using "[bold]{target_expression}[/bold]":')

    if sentence_input is None:
        sentence = _default_answer_input("Your sentence: ")
    else:
        sentence = sentence_input()

    result = request_correction(target_expression, sentence, base_url=base_url, model=model)

    if not result.available:
        feedback = "correction unavailable"
        console.print("[yellow]Sorry, sentence correction is unavailable right now.[/yellow]")
    elif result.uses_expression is False:
        feedback = "missing target expression"
        console.print(f'[yellow]Your sentence does not use "{target_expression}".[/yellow]')
    elif result.needs_correction:
        feedback = f"corrected: {result.corrected}"
        console.print(f"[red]Original:[/red]  {sentence}")
        console.print(f"[green]Corrected:[/green] {result.corrected}")
        if result.explanation:
            console.print(f"Explanation: {result.explanation}")
    else:
        feedback = "already correct"
        console.print("[green]Your sentence is already correct and natural.[/green]")

    return sentence, feedback


def run_session(
    vocab_dir: Path,
    progress_file: Path,
    group: str | None = None,
    ollama_url: str = "http://localhost:11434",
    model: str = DEFAULT_MODEL,
) -> None:
    """Run a full practice session: load items, filter, then walk forward
    through the recall step for each one, one at a time, no skip/back
    (FR-015, FR-016)."""
    items, warnings = load_vocabulary(vocab_dir)
    for warning in warnings:
        console.print(f"[yellow]Warning:[/yellow] {warning}")

    if group is not None:
        items = [item for item in items if item.group == group]

    if not items:
        console.print("No vocabulary items available for this session.")
        return

    for item in items:
        recall_attempt = run_recall_step(item)
        sentence, feedback = run_sentence_step(item.english, base_url=ollama_url, model=model)
        attempt = PracticeAttempt(
            timestamp=recall_attempt.timestamp,
            item=recall_attempt.item,
            answer=recall_attempt.answer,
            correct=recall_attempt.correct,
            sentence=sentence,
            feedback=feedback,
        )
        append_attempt(progress_file, attempt)
        print()
