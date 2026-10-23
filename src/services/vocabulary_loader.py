"""Loads VocabularyItems from every Markdown file in a directory (FR-001, FR-013).

Spec 023: the folder's shared corrections (`.corrections.json` overlay)
are applied on top of the files, which are never written."""

from pathlib import Path

from src.lib.markdown_blocks import parse_blocks
from src.models.vocabulary_item import VocabularyItem, VocabularyItemError
from src.services import corrections_file


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
    overlay = corrections_file.read(vocab_dir).overlay

    for md_file in sorted(vocab_dir.glob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        blocks, parse_warnings = parse_blocks(text)
        warnings.extend(f"{md_file.name}: {w}" for w in parse_warnings)

        for block in blocks:
            try:
                item = VocabularyItem.from_block(block)
            except VocabularyItemError as exc:
                warnings.append(f"{md_file.name}: {exc}")
                continue
            item.source = md_file
            _apply_overlay(item, overlay)
            items.append(item)
            if item.ipa_problem:
                warnings.append(
                    f"{md_file.name}: '{item.english}': {item.ipa_problem} — shown without one"
                )
            if item.pos_problem:
                warnings.append(
                    f"{md_file.name}: '{item.english}': {item.pos_problem} — shown without one"
                )

    return items, warnings


def _apply_overlay(item: VocabularyItem, overlay: dict) -> None:
    """Replace ipa, chinese and pos with the shared correction for this word,
    matched by the file meaning (origin_chinese, set by from_block)."""
    key = corrections_file.overlay_key(
        item.source.name, item.group, item.english, item.origin_chinese
    )
    values = overlay.get(key)
    if values is not None:
        item.ipa, item.chinese, item.pos = values.ipa, values.chinese, list(values.pos)
        # The corrected values passed the checks; the file's problems no longer apply.
        item.ipa_problem = item.pos_problem = None
