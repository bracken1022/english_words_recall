from pathlib import Path

from src.services.vocabulary_loader import load_vocabulary


def test_valid_file_loads_items(tmp_path: Path):
    vocab_file = tmp_path / "unit1.md"
    vocab_file.write_text(
        """
---
english: receive
chinese: 收到
alternates: [accept]
group: unit1
---
"""
    )
    items, warnings = load_vocabulary(tmp_path)
    assert warnings == []
    assert len(items) == 1
    assert items[0].english == "receive"
    assert items[0].alternates == ["accept"]
    assert items[0].group == "unit1"


def test_block_missing_required_field_is_skipped_rest_still_loads(tmp_path: Path):
    vocab_file = tmp_path / "unit1.md"
    vocab_file.write_text(
        """
---
chinese: 收到
---

---
english: give up
chinese: 放弃
---
"""
    )
    items, warnings = load_vocabulary(tmp_path)
    assert len(warnings) == 1
    assert len(items) == 1
    assert items[0].english == "give up"


def test_multiple_files_are_combined(tmp_path: Path):
    (tmp_path / "a.md").write_text("---\nenglish: receive\nchinese: 收到\n---\n")
    (tmp_path / "b.md").write_text("---\nenglish: give up\nchinese: 放弃\n---\n")
    items, warnings = load_vocabulary(tmp_path)
    assert warnings == []
    assert {item.english for item in items} == {"receive", "give up"}


def test_empty_directory_yields_empty_pool(tmp_path: Path):
    items, warnings = load_vocabulary(tmp_path)
    assert items == []
    assert warnings == []
