"""VocabularyItem: a single English expression to learn (data-model.md)."""

from dataclasses import dataclass, field


class VocabularyItemError(ValueError):
    """Raised when a vocabulary block is missing a required field."""


@dataclass
class VocabularyItem:
    english: str
    chinese: str
    alternates: list[str] = field(default_factory=list)
    group: str | None = None

    def __post_init__(self) -> None:
        if not self.english:
            raise VocabularyItemError("VocabularyItem requires a non-empty 'english' field")
        if not self.chinese:
            raise VocabularyItemError("VocabularyItem requires a non-empty 'chinese' field")

    @classmethod
    def from_block(cls, block: dict) -> "VocabularyItem":
        if "english" not in block or "chinese" not in block:
            raise VocabularyItemError(
                f"vocabulary block missing 'english' or 'chinese': {block!r}"
            )
        return cls(
            english=block["english"],
            chinese=block["chinese"],
            alternates=list(block.get("alternates") or []),
            group=block.get("group"),
        )

    def accepted_expressions(self) -> list[str]:
        return [self.english, *self.alternates]
