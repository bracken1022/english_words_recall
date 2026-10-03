"""Unit tests for src/lib/alternates.py (spec 018 FR-011, research R6,
contracts/enrichment-validation.md § Alternates): model-proposed
alternates are kept only when they are spelling variants."""

import pytest

from src.lib.alternates import filter_alternates, is_spelling_variant


@pytest.mark.parametrize(
    "a, b",
    [
        ("tyre", "tire"),
        ("epitomise", "epitomize"),
        ("colour", "color"),
        ("centre", "center"),
        ("travelled", "traveled"),
        ("e-mail", "email"),
        ("analyse", "analyze"),
        ("defence", "defense"),
        ("grey", "gray"),
        ("organisation", "organization"),
        ("anaemia", "anemia"),
        ("catalogue", "catalog"),
        ("programme", "program"),
        ("Colour", "color"),
        ("make-up", "make up"),
        ("realised", "realized"),
        ("favourite", "favorite"),
    ],
)
def test_spelling_variants(a, b):
    assert is_spelling_variant(a, b)
    assert is_spelling_variant(b, a)


@pytest.mark.parametrize(
    "a, b",
    [
        ("arduous", "difficult"),
        ("zealous", "enthusiastic"),
        ("affect", "effect"),
        ("accept", "except"),
        ("big", "large"),
        ("tire", "tired"),
        ("form", "from"),
        ("rise", "rize"),
        ("colour", "colour"),
        ("Color", "color"),
        ("hour", "hor"),
    ],
)
def test_not_spelling_variants(a, b):
    assert not is_spelling_variant(a, b)


def test_supplied_alternates_always_kept_first():
    kept, dropped = filter_alternates("arduous", ["difficult"], ["hard"])
    assert kept == ["difficult"]
    assert dropped == ["hard"]


def test_proposed_variants_kept_synonyms_dropped():
    kept, dropped = filter_alternates("tyre", [], ["tire", "wheel", "tyres"])
    assert kept == ["tire"]
    assert dropped == ["wheel", "tyres"]


def test_dedupe_and_drop_equal_or_empty():
    kept, dropped = filter_alternates("colour", ["Color"], ["color", "Colour", "  ", "colour"])
    assert kept == ["Color"]
    assert dropped == ["color", "Colour", "  ", "colour"]


def test_entries_are_trimmed():
    kept, _ = filter_alternates("tyre", [], ["  tire "])
    assert kept == ["tire"]


def test_at_most_five_and_length_limit():
    supplied = ["a1", "a2", "a3", "a4", "a5", "a6"]
    kept, _ = filter_alternates("word", supplied, [])
    assert kept == supplied[:5]

    long = "x" * 65
    kept, dropped = filter_alternates("word", [long], [])
    assert kept == []
    assert dropped == [long]


def test_empty_is_valid():
    assert filter_alternates("arduous", [], []) == ([], [])
