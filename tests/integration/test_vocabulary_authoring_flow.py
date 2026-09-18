from pathlib import Path

from src.services.vocabulary_loader import load_vocabulary


def test_new_item_added_to_file_is_available_after_reload(tmp_path: Path):
    vocab_file = tmp_path / "unit1.md"
    vocab_file.write_text("---\nenglish: receive\nchinese: 收到\n---\n")

    items, _ = load_vocabulary(tmp_path)
    assert {i.english for i in items} == {"receive"}

    # Simulate a person hand-editing the file to add a new item, then the
    # app being (re)started (FR-012).
    vocab_file.write_text(
        "---\nenglish: receive\nchinese: 收到\n---\n\n---\nenglish: give up\nchinese: 放弃\n---\n"
    )
    items, warnings = load_vocabulary(tmp_path)
    assert warnings == []
    assert {i.english for i in items} == {"receive", "give up"}


def test_malformed_block_skipped_valid_block_in_same_file_still_loads(tmp_path: Path):
    vocab_file = tmp_path / "unit1.md"
    vocab_file.write_text(
        "---\nchinese: 收到\n---\n\n---\nenglish: give up\nchinese: 放弃\n---\n"
    )
    items, warnings = load_vocabulary(tmp_path)
    assert len(warnings) == 1
    assert len(items) == 1
    assert items[0].english == "give up"
