"""IPA pronunciation values for vocabulary (spec 017, data-model.md).

normalize_ipa() turns a raw `ipa` field into the bare transcription stored
on a VocabularyItem (or reports why it can't be used); display_ipa() adds
the slashes for showing it."""

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


def _syllables(word: str) -> int:
    count, in_vowel = 0, False
    for ch in word:
        if ch in _VOWELS:
            if not in_vowel:
                count += 1
            in_vowel = True
        else:
            in_vowel = False
            if ch == _SYLLABIC:
                count += 1
    return count


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

    words = ipa.split()
    for word in words:
        if word.count("ˈ") > 1:
            problems.append(f'more than one primary stress in "{word}"')
        if word.strip("()") in _UNSTRESSED:
            continue
        if _syllables(word) < 2:
            continue
        if len(words) == 1 and "ˈ" not in word:
            problems.append(f'no primary stress (ˈ) in "{word}"')
        elif len(words) > 1 and "ˈ" not in word and "ˌ" not in word:
            # In a phrase each longer content word carries some stress.
            problems.append(f'no stress mark in "{word}"')
    if len(words) > 1 and sum(_syllables(w) for w in words) >= 2 and "ˈ" not in ipa:
        problems.append("no primary stress (ˈ) in the phrase")
    return problems
