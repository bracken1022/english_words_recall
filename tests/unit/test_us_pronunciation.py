"""Unit tests for American IPA from the CMU Pronouncing Dictionary (spec
018 research R4, revised): ARPABET entries are converted to the Oxford
Learner's Dictionaries NAmE style that check_american_ipa() enforces."""

import pytest

from src.lib.ipa import check_american_ipa
from src.lib.us_pronunciation import arpabet_to_ipa, lookup_american_ipa


@pytest.mark.parametrize(
    "english, expected",
    [
        ("zealous", "ˈzeləs"),
        ("receive", "rəˈsiːv"),
        ("car", "kɑːr"),
        ("go", "ɡoʊ"),
        ("thought", "θɔːt"),
        ("bird", "bɜːrd"),
        ("water", "ˈwɔːtər"),
        ("better", "ˈbetər"),
        ("color", "ˈkʌlər"),
        ("here", "hɪr"),
        ("care", "ker"),
        ("sure", "ʃʊr"),
        ("career", "kəˈrɪr"),
        ("garage", "ɡəˈrɑːʒ"),
        ("hurry", "ˈhɜːri"),
        ("squirrel", "ˈskwɜːrəl"),
        ("forward", "ˈfɔːrwərd"),
        ("nation", "ˈneɪʃn"),
        ("often", "ˈɔːfn"),
        ("substantial", "səbˈstænʃl"),
        ("tire", "ˈtaɪər"),
        ("tyre", "ˈtaɪər"),
        ("hierarchy", "ˈhaɪərɑːrki"),
        ("temporary", "ˈtempəreri"),
        ("library", "ˈlaɪbreri"),
        ("information", "ˌɪnfərˈmeɪʃn"),
        ("abundant", "əˈbʌndənt"),
        ("arduous", "ˈɑːrdʒuəs"),
        ("pursue", "pərˈsuː"),
        ("person", "ˈpɜːrsn"),
        ("question", "ˈkwestʃən"),
        ("tomato", "təˈmeɪtoʊ"),
        ("coffee", "ˈkɑːfi"),
        ("epitomize", "ɪˈpɪtəmaɪz"),
        ("meticulous", "məˈtɪkjələs"),
        ("dance", "dæns"),
        ("vitamin", "ˈvaɪtəmən"),
        ("diligent", "ˈdɪlɪdʒənt"),
    ],
)
def test_single_words(english, expected):
    result = lookup_american_ipa(english)
    assert result.ipa == expected
    assert check_american_ipa(result.ipa) == []


@pytest.mark.parametrize(
    "english, expected",
    [
        ("give up", "ˌɡɪv ˈʌp"),
        ("tend to", "ˈtend tə"),
        ("look forward to", "ˌlʊk ˈfɔːrwərd tə"),
        ("take off", "ˌteɪk ˈɔːf"),
        ("make up for", "ˌmeɪk ˈʌp fər"),
        ("pay attention", "ˌpeɪ əˈtenʃn"),
    ],
)
def test_phrases(english, expected):
    result = lookup_american_ipa(english)
    assert result.ipa == expected
    assert check_american_ipa(result.ipa) == []


def test_case_and_spaces_ignored():
    assert lookup_american_ipa("  Zealous ").ipa == "ˈzeləs"


def test_unknown_word():
    result = lookup_american_ipa("zxqvword")
    assert result.ipa is None
    assert result.ambiguous is False


def test_unknown_word_in_phrase():
    assert lookup_american_ipa("give zxqvword").ipa is None


def test_spelling_variant_fallback():
    assert lookup_american_ipa("epitomise").ipa is None
    assert lookup_american_ipa("epitomise", variants=["epitomize"]).ipa == "ɪˈpɪtəmaɪz"


@pytest.mark.parametrize("english", ["research", "advertisement"])
def test_stress_shift_entries_are_ambiguous(english):
    # research: R IY0 S ER1 CH / R IY1 S ER0 CH — which one is meant?
    result = lookup_american_ipa(english)
    assert result.ambiguous is True
    assert result.ipa is None


def test_vowel_only_variants_use_first_entry():
    # either: IY1 DH ER0 / AY1 DH ER0, same stress → first entry
    result = lookup_american_ipa("either")
    assert result.ambiguous is False
    assert result.ipa == "ˈiːðər"


@pytest.mark.parametrize(
    "phones, expected",
    [
        ("HH AW1 ER0", "ˈhaʊər"),
        ("Z IY1 R OW0", "ˈzɪroʊ"),
        ("AE1 K CH UW0 AH0 L", "ˈæktʃuəl"),
        ("AA1 R G Y UW0", "ˈɑːrɡjuː"),
        ("M OW1 B AH0 L", "ˈmoʊbl"),
        ("L AH1 N D AH0 N", "ˈlʌndən"),
        ("S T R IY1 T", "striːt"),
        ("IH0 K S T R AE1 K T", "ɪkˈstrækt"),
    ],
)
def test_arpabet_conversion(phones, expected):
    assert arpabet_to_ipa(phones.split()) == expected
