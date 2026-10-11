"""Unit tests for src/lib/word_forms.py (spec 021, research R4): does an
example sentence use the word, allowing natural inflected forms?"""

import pytest

from src.lib.word_forms import IRREGULAR_VERBS, contains_form


@pytest.mark.parametrize(
    "english, sentence",
    [
        ("zealous", "She is zealous."),
        ("receive", "I received it."),
        ("receive", "We are receiving guests."),
        ("study", "He studies hard."),
        ("study", "She studied all night."),
        ("stop", "The bus stopped here."),
        ("stop", "Stopping now is hard."),
        ("make", "I am making tea."),
        ("give up", "They gave it up."),
        ("give up", "Never gave up hope."),
        ("tend to", "Prices tend to rise."),
        ("tend to", "It tends to rain in spring."),
        ("take off", "The plane took off late."),
        ("look forward to", "I'm looking forward to it."),
        ("rent", "RENT is due!"),
        ("run out of", "We ran out of milk."),
        ("get along with", "She gets along with everyone."),
        ("in charge of", "He is in charge of sales."),
        ("withstand", "The wall withstood the storm."),
    ],
)
def test_contains(english, sentence):
    assert contains_form(sentence, english)


@pytest.mark.parametrize(
    "english, sentence",
    [
        ("zealous", "She is zeal."),
        ("rent", "My parent is here."),
        ("give up", "Give the old man a chance to get up."),
        ("zealous", ""),
        ("tend to", "Tend the garden."),
    ],
)
def test_not_contains(english, sentence):
    assert not contains_form(sentence, english)


def test_irregular_table_size():
    assert len(IRREGULAR_VERBS) >= 120
