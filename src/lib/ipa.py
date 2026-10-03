"""IPA pronunciation values for vocabulary (spec 017, data-model.md).

normalize_ipa() turns a raw `ipa` field into the bare transcription stored
on a VocabularyItem (or reports why it can't be used); display_ipa() adds
the slashes for showing it. check_british_ipa() vets spec 017's British
fill; check_american_ipa() and is_heteronym() vet the American IPA the
local model generates for uploads (spec 018, research R4)."""

import re
import unicodedata

MAX_IPA_LENGTH = 100


def _is_letter(ch: str) -> bool:
    # Stress and length marks (ˈ ˌ ː) are "modifier letters" (Lm) to
    # str.isalpha(); a pronunciation needs at least one real letter.
    return unicodedata.category(ch) in ("Ll", "Lu", "Lo")


def normalize_ipa(raw) -> tuple[str | None, str | None]:
    """Return (ipa, problem): the bare transcription, or None plus a
    human-readable reason when *raw* isn't a usable pronunciation."""
    if raw is None:
        return None, None
    problem = f'ipa "{raw}" is not a pronunciation'
    if not isinstance(raw, str):
        return None, problem

    value = raw.strip()
    if len(value) >= 2 and (value[0], value[-1]) in (("/", "/"), ("[", "]")):
        value = value[1:-1].strip()

    if (
        not value
        or len(value) > MAX_IPA_LENGTH
        or any(c.isascii() and c.isdigit() for c in value)
        or not any(_is_letter(c) for c in value)
    ):
        return None, problem
    return value, None


def display_ipa(ipa: str | None) -> str:
    return f"/{ipa}/" if ipa else ""


# --- British (RP) checks for filled pronunciations (research.md R6) ----------

_CONSONANTS = set("pbtdkɡfvθðszʃʒhmnŋlrjw")
_VOWELS = set("iɪeæʌɒɔʊuəɑɜa")
_MARKS = set("ˈˌː()")
_SYLLABIC = "̩"
_ALLOWED = _CONSONANTS | _VOWELS | _MARKS | {" ", _SYLLABIC}
# Weak forms of function words, which dictionaries leave unstressed.
_UNSTRESSED = {"tə", "tʊ", "ə", "ən", "ðə", "əv", "fə", "frəm", "ənd", "ət", "əz", "ɪn", "ɒn"}


def _syllables(word: str, vowels: set[str] = _VOWELS) -> int:
    count, in_vowel = 0, False
    for ch in word:
        if ch in vowels:
            if not in_vowel:
                count += 1
            in_vowel = True
        else:
            in_vowel = False
            if ch == _SYLLABIC:
                count += 1
    return count


def _stress_problems(ipa: str, unstressed: set[str], vowels: set[str]) -> list[str]:
    """Missing or doubled stress marks: a word of two or more syllables
    needs a primary stress (in a phrase, some stress), weak forms of
    function words excepted, and a phrase needs one primary stress."""
    problems: list[str] = []
    words = ipa.split()
    for word in words:
        if word.count("ˈ") > 1:
            problems.append(f'more than one primary stress in "{word}"')
        if word.strip("()") in unstressed:
            continue
        if _syllables(word, vowels) < 2:
            continue
        if len(words) == 1 and "ˈ" not in word:
            problems.append(f'no primary stress (ˈ) in "{word}"')
        elif len(words) > 1 and "ˈ" not in word and "ˌ" not in word:
            # In a phrase each longer content word carries some stress.
            problems.append(f'no stress mark in "{word}"')
    if len(words) > 1 and sum(_syllables(w, vowels) for w in words) >= 2 and "ˈ" not in ipa:
        problems.append("no primary stress (ˈ) in the phrase")
    return problems


def check_british_ipa(ipa: str) -> list[str]:
    """Problems with a filled British IPA transcription; [] means it passes.
    Catches non-IPA or American symbols, missing/doubled primary stress and
    rhotic r — not wrong vowels, which still need a human spot check."""
    problems: list[str] = []

    if "g" in ipa:
        problems.append("use ɡ (U+0261), not g")
    bad = sorted({ch for ch in ipa if ch not in _ALLOWED and ch != "g"})
    if bad:
        problems.append(f"not British IPA: {' '.join(bad)}")

    # The dictionaries' optional linking "(r)" is fine; any other r must be
    # followed by a vowel (non-rhotic).
    # Stress marks may sit between a linking r and its vowel (ˌkaʊntərˈækt).
    plain = ipa.replace("(r)", "").replace("ˈ", "").replace("ˌ", "")
    for index, ch in enumerate(plain):
        if ch == "r" and (index + 1 >= len(plain) or plain[index + 1] not in _VOWELS):
            problems.append("non-rhotic British IPA: no r before a consonant or at the end")
            break

    problems.extend(_stress_problems(ipa, _UNSTRESSED, _VOWELS))
    return problems


# --- American (OALD NAmE) checks for generated pronunciations (spec 018) ----

_US_CONSONANTS = set("pbtdkɡfvθðszʃʒhmnŋlrjw")
_US_VOWELS = set("iɪeæʌɑɔʊuəɜao")
_FLAP = "̬"
_US_ALLOWED = _US_CONSONANTS | _US_VOWELS | set("ˈˌː") | {" ", _SYLLABIC, _FLAP}
_US_UNSTRESSED = {"tə", "tʊ", "ə", "ən", "ðə", "əv", "fər", "frəm", "ənd", "ət", "əz", "ɪn", "ɑn"}

# British forms that NAmE never uses: ɒ, əʊ, centring diphthongs (except
# inside aɪə/eɪə/ɔɪə and aʊə/oʊə, as in tire and hour), linking (r), and
# ɜː without its r.
_BRITISH_MARKERS = [
    ("ɒ", re.compile("ɒ")),
    ("əʊ", re.compile("əʊ")),
    ("(r)", re.compile(r"\(r\)")),
    ("ɪə", re.compile("(?<![aeɔ])ɪə")),
    ("eə", re.compile("eə")),
    ("ʊə", re.compile("(?<![ao])ʊə")),
    # A stress mark may sit between ɜː and its r (ˌekstrətɜːˈrestriəl).
    ("ɜː without r", re.compile("ɜː(?![ˈˌ]?r)")),
]

# Words whose pronunciation depends on which meaning is meant (stress
# shifts like REcord/reCORD, or different vowels like tear/tear). Without
# the meaning, a generated pronunciation would be a guess (FR-009).
HETERONYMS = frozenset(
    {
        "address", "advocate", "alternate", "appropriate", "articulate", "associate",
        "attribute", "bass", "bow", "close", "combat", "compact", "compound", "conduct",
        "conflict", "console", "content", "contest", "contract", "convert", "convict",
        "decrease", "delegate", "deliberate", "desert", "digest", "discount", "does",
        "dove", "duplicate", "entrance", "estimate", "export", "extract", "graduate",
        "import", "increase", "insult", "intimate", "invalid", "lead", "live", "minute",
        "moderate", "object", "perfect", "permit", "polish", "present", "produce",
        "progress", "project", "protest", "read", "rebel", "record", "refuse", "resume",
        "row", "separate", "sow", "subject", "survey", "suspect", "tear", "upset", "use",
        "wind", "wound",
    }
)


def is_heteronym(english: str) -> bool:
    return english.strip().casefold() in HETERONYMS


def check_american_ipa(ipa: str) -> list[str]:
    """Problems with a generated American IPA transcription in the Oxford
    Learner's Dictionaries NAmE style; [] means it passes. Like the British
    check it catches symbols and stress, not wrong vowels."""
    problems: list[str] = []
    if "g" in ipa:
        problems.append("use ɡ (U+0261), not g")
    problems.extend(
        f"British IPA marker: {name}" for name, pattern in _BRITISH_MARKERS if pattern.search(ipa)
    )
    bad = sorted(
        {ch for ch in ipa.replace("(r)", "") if ch not in _US_ALLOWED and ch not in "gɒ"}
    )
    if bad:
        problems.append(f"not American IPA (OALD NAmE style): {' '.join(bad)}")
    problems.extend(_stress_problems(ipa, _US_UNSTRESSED, _US_VOWELS))
    return problems
