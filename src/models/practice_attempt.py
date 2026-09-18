"""PracticeAttempt: one learner interaction with a VocabularyItem (data-model.md)."""

from dataclasses import dataclass


class PracticeAttemptError(ValueError):
    """Raised when a practice-attempt block is invalid."""


@dataclass
class PracticeAttempt:
    timestamp: str
    item: str
    answer: str
    correct: bool
    sentence: str | None = None
    feedback: str | None = None

    def __post_init__(self) -> None:
        if not self.timestamp:
            raise PracticeAttemptError("PracticeAttempt requires a non-empty 'timestamp'")
        if not self.item:
            raise PracticeAttemptError("PracticeAttempt requires a non-empty 'item'")
        if self.answer is None:
            raise PracticeAttemptError("PracticeAttempt requires 'answer' (may be empty string)")
        if not isinstance(self.correct, bool):
            raise PracticeAttemptError("PracticeAttempt requires 'correct' to be a boolean")
        if (self.sentence is None) != (self.feedback is None):
            raise PracticeAttemptError(
                "PracticeAttempt requires 'sentence' and 'feedback' to be both present or both absent"
            )

    @classmethod
    def from_block(cls, block: dict) -> "PracticeAttempt":
        required = ("timestamp", "item", "answer", "correct")
        missing = [f for f in required if f not in block]
        if missing:
            raise PracticeAttemptError(f"practice-attempt block missing fields {missing}: {block!r}")
        return cls(
            timestamp=block["timestamp"],
            item=block["item"],
            answer=block["answer"],
            correct=bool(block["correct"]),
            sentence=block.get("sentence"),
            feedback=block.get("feedback"),
        )
