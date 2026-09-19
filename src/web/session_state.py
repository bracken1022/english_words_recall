"""The shared, in-memory practice-session state machine (spec 003,
data-model.md). A thin orchestration layer over the existing, unchanged
services — vocabulary_loader, matcher, llm_client.request_correction,
progress_log — introducing no new grading/review/persistence logic."""

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from src.models.practice_attempt import PracticeAttempt
from src.services.llm_client import CorrectionResult, request_correction
from src.services.matcher import grade_answer
from src.services.progress_log import append_attempt
from src.services.vocabulary_loader import load_vocabulary

Step = str  # "empty" | "recall" | "sentence" | "feedback" | "complete"


class WrongStepError(Exception):
    """Raised when an action is requested for the wrong step (no state change)."""


class PracticeSession:
    def __init__(self, vocab_dir: Path, progress_file: Path, group: str | None = None):
        self.progress_file = progress_file
        self.warnings: list[str] = []
        self.current_index = 0
        self.pending_attempt: dict | None = None
        self.last_correction: CorrectionResult | None = None
        self._review_in_progress = False
        self.correct_count = 0

        items, warnings = load_vocabulary(vocab_dir)
        self.warnings = warnings
        if group is not None:
            items = [item for item in items if item.group == group]
        self.items = items

        self.step: Step = "recall" if self.items else "empty"

    @property
    def current_item(self):
        return self.items[self.current_index]

    def submit_answer(self, answer: str) -> dict:
        if self.step != "recall":
            raise WrongStepError("not awaiting an answer")

        item = self.current_item
        correct = grade_answer(item, answer)
        self.pending_attempt = {
            "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
            "item": item.english,
            "answer": answer,
            "correct": correct,
        }
        self.step = "sentence"
        return {"correct": correct, "accepted_expressions": item.accepted_expressions()}

    def submit_sentence(
        self,
        sentence: str,
        base_url: str,
        model: str,
        correction_fn: Callable[..., CorrectionResult] | None = None,
    ) -> dict:
        if self.step != "sentence":
            raise WrongStepError("not awaiting a sentence")
        if self._review_in_progress:
            raise WrongStepError("a sentence review is already in progress")

        # Resolved from the module global at call time (not bound as a
        # default argument) so tests can patch `request_correction` here.
        if correction_fn is None:
            correction_fn = request_correction

        self._review_in_progress = True
        try:
            item = self.current_item
            result = correction_fn(item.english, sentence, base_url=base_url, model=model)
        finally:
            self._review_in_progress = False

        self.last_correction = result

        if not result.available:
            feedback = "correction unavailable"
        elif result.uses_expression is False:
            feedback = "missing target expression"
        elif result.needs_correction:
            feedback = f"corrected: {result.corrected}"
        else:
            feedback = "already correct"

        self.pending_attempt["sentence"] = sentence
        self.pending_attempt["feedback"] = feedback

        attempt = PracticeAttempt(**self.pending_attempt)
        append_attempt(self.progress_file, attempt)

        self.step = "feedback"
        return {
            "available": result.available,
            "uses_expression": result.uses_expression,
            "needs_correction": result.needs_correction,
            "corrected": result.corrected,
            "explanation": result.explanation,
        }

    def skip_sentence(self) -> None:
        """Skip the sentence-writing step for the current item without a
        correction request, recording the recall outcome as-is (spec 006).
        Goes straight from "sentence" to "recall"/"complete", never
        visiting "feedback" — see data-model.md's state-machine table."""
        if self.step != "sentence":
            raise WrongStepError("not awaiting a sentence")

        attempt = PracticeAttempt(**self.pending_attempt)
        append_attempt(self.progress_file, attempt)

        if self.pending_attempt["correct"]:
            self.correct_count += 1

        self.pending_attempt = None
        self.last_correction = None
        self.current_index += 1
        self.step = "complete" if self.current_index >= len(self.items) else "recall"

    def continue_to_next(self) -> None:
        if self.step == "complete":
            return
        if self.step != "feedback":
            raise WrongStepError("not ready to continue")

        if self.pending_attempt["correct"]:
            self.correct_count += 1

        self.pending_attempt = None
        self.last_correction = None
        self.current_index += 1
        self.step = "complete" if self.current_index >= len(self.items) else "recall"

    def state(self) -> dict:
        base = {"step": self.step, "warnings": self.warnings}
        if self.step == "complete":
            base["total"] = len(self.items)
            base["correct"] = self.correct_count
            return base
        if self.step == "empty":
            return base

        item = self.current_item
        base["chinese"] = item.chinese

        if self.step in ("sentence", "feedback"):
            base["accepted_expressions"] = item.accepted_expressions()
            base["answer"] = self.pending_attempt["answer"]
            base["correct"] = self.pending_attempt["correct"]

        if self.step == "feedback":
            base["sentence"] = self.pending_attempt["sentence"]
            base["feedback"] = {
                "available": self.last_correction.available,
                "uses_expression": self.last_correction.uses_expression,
                "needs_correction": self.last_correction.needs_correction,
                "corrected": self.last_correction.corrected,
                "explanation": self.last_correction.explanation,
            }

        return base
