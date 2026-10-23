"""VocabularyItem: a single English expression to learn (data-model.md)."""

from dataclasses import dataclass, field
from pathlib import Path

from src.lib.ipa import normalize_ipa
from src.lib.pos import normalize_pos


class VocabularyItemError(ValueError):
    """Raised when a vocabulary block is missing a required field."""


@dataclass
class VocabularyItem:
    english: str
    chinese: str
    alternates: list[str] = field(default_factory=list)
    group: str | None = None
    # IPA without slashes: British for the shared/017 fill, American for
    # spec 018 imports. ipa_problem records why a block's ipa value was
    # rejected; the word still loads without one.
    ipa: str | None = None
    ipa_problem: str | None = field(default=None, compare=False, repr=False)
    # Part-of-speech labels (spec 019), e.g. ["n.", "v."]; never graded.
    pos: list[str] = field(default_factory=list)
    pos_problem: str | None = field(default=None, compare=False, repr=False)
    # The file the word was loaded from (spec 020), so it can be removed.
    source: Path | None = field(default=None, compare=False, repr=False)
    # A saved example sentence and its translation (spec 021).
    example: str | None = field(default=None, compare=False, repr=False)
    example_zh: str | None = field(default=None, compare=False, repr=False)
    # The meaning as written in the file (spec 023, research R4): a shared
    # word's identity in hidden words, saved examples and corrections,
    # which stays put when a shared correction changes `chinese`.
    origin_chinese: str | None = field(default=None, compare=False, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.english, str):
            raise VocabularyItemError("VocabularyItem requires 'english' to be a string")
        if not self.english:
            raise VocabularyItemError("VocabularyItem requires a non-empty 'english' field")
        if not isinstance(self.chinese, str):
            raise VocabularyItemError("VocabularyItem requires 'chinese' to be a string")
        if not self.chinese:
            raise VocabularyItemError("VocabularyItem requires a non-empty 'chinese' field")
        if not all(isinstance(a, str) for a in self.alternates):
            raise VocabularyItemError("VocabularyItem requires every 'alternates' entry to be a string")
        if self.group is not None and not isinstance(self.group, str):
            raise VocabularyItemError("VocabularyItem requires 'group' to be a string or absent")
        if self.ipa is not None and not isinstance(self.ipa, str):
            raise VocabularyItemError("VocabularyItem requires 'ipa' to be a string or absent")
        if not isinstance(self.pos, list) or not all(isinstance(p, str) for p in self.pos):
            raise VocabularyItemError("VocabularyItem requires 'pos' to be a list of labels")
        if self.origin_chinese is None:
            self.origin_chinese = self.chinese

    @classmethod
    def from_block(cls, block: dict) -> "VocabularyItem":
        if "english" not in block or "chinese" not in block:
            raise VocabularyItemError(
                f"vocabulary block missing 'english' or 'chinese': {block!r}"
            )
        ipa, ipa_problem = normalize_ipa(block.get("ipa"))
        pos, pos_problem = normalize_pos(block.get("pos"))
        return cls(
            english=block["english"],
            chinese=block["chinese"],
            alternates=list(block.get("alternates") or []),
            group=block.get("group"),
            ipa=ipa,
            ipa_problem=ipa_problem,
            pos=pos or [],
            pos_problem=pos_problem,
            example=_text(block.get("example")),
            example_zh=_text(block.get("example_zh")),
        )

    def accepted_expressions(self) -> list[str]:
        return [self.english, *self.alternates]


def _text(value) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None
