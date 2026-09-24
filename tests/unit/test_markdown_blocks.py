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


def test_yaml_1_1_boolean_words_stay_strings():
    """Regression guard: PyYAML's default (YAML 1.1) resolver silently
    turns unquoted "on"/"off"/"yes"/"no" (any case) into booleans — a real
    hazard here, since these are all ordinary English words a learner
    might add as vocabulary content. This format never has a legitimate
    use for those spellings as booleans, so they must stay strings."""
    text = """
---
english: on
chinese: 在……上
alternates: [off, Yes, NO, y, n]
---
"""
    blocks, warnings = parse_blocks(text)
    assert warnings == []
    assert blocks == [
        {
            "english": "on",
            "chinese": "在……上",
            "alternates": ["off", "Yes", "NO", "y", "n"],
        }
    ]


def test_canonical_true_false_still_parse_as_real_booleans():
    """The progress log's "correct" field is a genuine boolean, always
    written as the canonical true/false spelling (progress_log.py) — the
    narrowed bool resolver must still recognize exactly that spelling."""
    text = """
---
timestamp: t1
item: receive
answer: receive
correct: true
---
"""
    blocks, warnings = parse_blocks(text)
    assert warnings == []
    assert blocks[0]["correct"] is True
