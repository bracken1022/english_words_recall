from src.lib.markdown_blocks import parse_blocks


def test_parses_single_well_formed_block():
    text = """
---
english: receive
chinese: 收到
---
"""
    blocks, warnings = parse_blocks(text)
    assert warnings == []
    assert blocks == [{"english": "receive", "chinese": "收到"}]


def test_parses_multiple_blocks_with_surrounding_prose():
    text = """
Some notes for the author.

---
english: receive
chinese: 收到
---

More notes.

---
english: give up
chinese: 放弃
---
"""
    blocks, warnings = parse_blocks(text)
    assert warnings == []
    assert blocks == [
        {"english": "receive", "chinese": "收到"},
        {"english": "give up", "chinese": "放弃"},
    ]


def test_malformed_block_produces_warning_not_exception():
    text = """
---
english: receive
chinese: [unclosed
---

---
english: give up
chinese: 放弃
---
"""
    blocks, warnings = parse_blocks(text)
    assert len(warnings) == 1
    assert blocks == [{"english": "give up", "chinese": "放弃"}]


def test_non_mapping_block_produces_warning():
    text = """
---
- just
- a
- list
---
"""
    blocks, warnings = parse_blocks(text)
    assert blocks == []
    assert len(warnings) == 1


def test_no_blocks_returns_empty_lists():
    blocks, warnings = parse_blocks("just some prose, no blocks here")
    assert blocks == []
    assert warnings == []
