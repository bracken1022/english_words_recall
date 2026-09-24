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


def test_alternate_that_is_a_yaml_1_1_boolean_word_loads_as_a_string(tmp_path: Path):
    """Regression test for the reported bug: an alternate expression like
    "on" (or "off"/"yes"/"no") must load as the literal word, not silently
    become a Python bool that later crashes grading."""
    vocab_file = tmp_path / "unit1.md"
    vocab_file.write_text(
        """
---
english: upon
alternates: [on]
chinese: 在……上；在……之上
group: u-words
---
"""
    )
    items, warnings = load_vocabulary(tmp_path)
    assert warnings == []
    assert len(items) == 1
    assert items[0].alternates == ["on"]
    assert items[0].accepted_expressions() == ["upon", "on"]


def test_block_with_non_string_alternate_is_skipped_as_warning_not_a_crash(tmp_path: Path):
    """Defense in depth beyond the boolean-resolver fix: an alternate
    that's some other non-string YAML scalar (e.g. an unquoted number)
    must be caught here, at load time, and turned into a skip+warning —
    the same "never crash the whole session on bad vocab data" contract
    load_vocabulary already documents for missing fields — rather than
    reaching grade_answer() and crashing mid-session."""
    vocab_file = tmp_path / "unit1.md"
    vocab_file.write_text(
        """
---
english: receive
chinese: 收到
alternates: [42]
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
