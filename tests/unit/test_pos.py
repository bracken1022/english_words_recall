"""Unit tests for src/lib/pos.py (spec 019 research R2): the fixed
part-of-speech labels and the normaliser that turns any accepted
spelling into them."""

import pytest

from src.lib.pos import (
    POS_LABELS,
    POS_NAMES,
    display_pos,
    is_pos_field,
    normalize_pos,
    strip_pos_notes,
)


def test_label_set():
    assert POS_LABELS == (
        "n.", "v.", "adj.", "adv.", "prep.", "conj.",
        "pron.", "det.", "int.", "num.", "phr. v.", "phr.",
    )  # fmt: skip
    assert set(POS_NAMES) == set(POS_LABELS)
    assert POS_NAMES["adj."] == "adjective"
    assert POS_NAMES["phr. v."] == "phrasal verb"


def test_none_is_absent():
    assert normalize_pos(None) == (None, None)


@pytest.mark.parametrize(
    "raw, labels",
    [
        ("adj.", ["adj."]),
        ("Adj", ["adj."]),
        ("adjective", ["adj."]),
        ("形容词", ["adj."]),
        (["n.", "v."], ["n.", "v."]),
        ("n. v.", ["n.", "v."]),
        ("n., v.", ["n.", "v."]),
        ("noun/verb", ["n.", "v."]),
        ("名词；动词", ["n.", "v."]),
        ("n、v", ["n.", "v."]),
        ("vt.", ["v."]),
        ("vi", ["v."]),
        ("及物动词", ["v."]),
        ("phrasal verb", ["phr. v."]),
        ("phr. v.", ["phr. v."]),
        ("phr.v.", ["phr. v."]),
        ("短语动词", ["phr. v."]),
        ("idiom", ["phr."]),
        ("短语", ["phr."]),
        ("art.", ["det."]),
        ("v. n. v.", ["v.", "n."]),
        ("adv. phr. v.", ["adv.", "phr. v."]),
        ("Interjection", ["int."]),
    ],
)
def test_normalize(raw, labels):
    assert normalize_pos(raw) == (labels, None)


@pytest.mark.parametrize("raw", ["verbish", "", "   ", 42, [], ["n.", 3], "n. foo"])
def test_invalid(raw):
    labels, problem = normalize_pos(raw)
    assert labels is None
    assert "is not a part of speech" in problem
    assert problem.startswith(f'pos "{raw}"')


@pytest.mark.parametrize("text", ["adj.", "n. v.", "noun", "形容词", "phr. v.", "Verb", "n./v."])
def test_is_pos_field(text):
    assert is_pos_field(text)


@pytest.mark.parametrize("text", ["n", "a", "v", "tire", "收到", "/rɪˈsiːv/", "", "art"])
def test_is_not_pos_field(text):
    assert not is_pos_field(text)


@pytest.mark.parametrize(
    "text, expected",
    [
        ("租金；租用；（动词）出租", "租金；租用；出租"),
        ("（名词）记录；(v.) 记录", "记录；记录"),
        ("热心的", "热心的"),
        ("（动词）", ""),
        ("（俚语）卑鄙的人", "（俚语）卑鄙的人"),
        ("老鼠；（动词）", "老鼠"),
    ],
)
def test_strip_pos_notes(text, expected):
    assert strip_pos_notes(text) == expected


def test_display_pos():
    assert display_pos(["n.", "v."]) == "n. v."
    assert display_pos([]) == ""
