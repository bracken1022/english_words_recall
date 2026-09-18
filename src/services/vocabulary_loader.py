"""Loads VocabularyItems from every Markdown file in a directory (FR-001, FR-013)."""

from pathlib import Path

from src.lib.markdown_blocks import parse_blocks
from src.models.vocabulary_item import VocabularyItem, VocabularyItemError


def load_vocabulary(vocab_dir: Path) -> tuple[list[VocabularyItem], list[str]]:
    """Load all VocabularyItems from the Markdown files in *vocab_dir*.

    Returns (items, warnings). A block that fails to parse, or that parses
    but is missing a required field, is skipped and reported as a warning;
    it never prevents the rest of the pool from loading.
    """
    items: list[VocabularyItem] = []
    warnings: list[str] = []

    if not vocab_dir.exists():
        return items, warnings

    for md_file in sorted(vocab_dir.glob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        blocks, parse_warnings = parse_blocks(text)
        warnings.extend(f"{md_file.name}: {w}" for w in parse_warnings)

        for block in blocks:
            try:
                items.append(VocabularyItem.from_block(block))
            except VocabularyItemError as exc:
                warnings.append(f"{md_file.name}: {exc}")

    return items, warnings
