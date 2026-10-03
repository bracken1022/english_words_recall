"""American IPA from the CMU Pronouncing Dictionary (spec 018, research R4).

The local model proved unreliable at IPA (eval-report.md), so imported
words take their pronunciation from CMUdict, a free offline dictionary of
General American English. Its ARPABET entries are converted to the Oxford
Learner's Dictionaries NAmE style that check_american_ipa() enforces:
length marks, every r written (ɑːr ɜːr ər), ɪr/er/ʊr before r, oʊ, ɡ,
syllabic n/l, stress marks before the syllable onset, no mark on a
one-syllable word, weak forms of function words in phrases.

The dictionary data (BSD-licensed, © Carnegie Mellon University) comes
from the `cmudict` package's data file; it is read directly."""

import re
from dataclasses import dataclass
from functools import cache
from importlib.resources import files

_CONSONANTS = {
    "B": "b", "CH": "tʃ", "D": "d", "DH": "ð", "F": "f", "G": "ɡ", "HH": "h",
    "JH": "dʒ", "K": "k", "L": "l", "M": "m", "N": "n", "NG": "ŋ", "P": "p",
    "R": "r", "S": "s", "SH": "ʃ", "T": "t", "TH": "θ", "V": "v", "W": "w",
    "Y": "j", "Z": "z", "ZH": "ʒ",
}  # fmt: skip

# Vowel → (stressed, unstressed) symbols.
_VOWELS = {
    "AA": ("ɑː", "ɑː"), "AE": ("æ", "æ"), "AH": ("ʌ", "ə"), "AO": ("ɔː", "ɔː"),
    "AW": ("aʊ", "aʊ"), "AY": ("aɪ", "aɪ"), "EH": ("e", "e"), "ER": ("ɜː", "ə"),
    "EY": ("eɪ", "eɪ"), "IH": ("ɪ", "ɪ"), "IY": ("iː", "i"), "OW": ("oʊ", "oʊ"),
    "OY": ("ɔɪ", "ɔɪ"), "UH": ("ʊ", "ʊ"), "UW": ("uː", "uː"),
}  # fmt: skip

# Before r, NAmE writes these vowels short: here hɪr, care ker, sure ʃʊr.
_BEFORE_R = {"IY": "ɪ", "EY": "e", "UW": "ʊ"}

# English syllable onsets (IPA tokens), for placing stress marks.
_ONSETS = {
    tuple(onset.split())
    for onset in [
        "p l", "b l", "k l", "ɡ l", "f l", "s l", "p r", "b r", "t r", "d r", "k r", "ɡ r",
        "f r", "θ r", "ʃ r", "p j", "b j", "k j", "ɡ j", "f j", "v j", "m j", "h j", "s w",
        "t w", "d w", "k w", "ɡ w", "θ w", "s p", "s t", "s k", "s m", "s n", "s f",
        "s p l", "s p r", "s t r", "s k r", "s k w", "s k j", "s p j",
    ]
} | {(c,) for c in _CONSONANTS.values() if c != "ŋ"}  # fmt: skip

# Word-final ə + n/l becomes syllabic n/l after these consonants (nation
# ˈneɪʃn, mobile ˈmoʊbl), as OALD writes them.
_SYLLABIC_N_AFTER = {"t", "d", "s", "z", "ʃ", "ʒ", "f", "v", "θ", "ð"}
_NOT_SYLLABIC_L_AFTER = {"l", "r", "w", "j", "n", "ŋ"}

# Weak forms of function words inside a phrase (tend to ˈtend tə).
_WEAK_FORMS = {
    "to": "tə", "for": "fər", "of": "əv", "a": "ə", "an": "ən", "the": "ðə",
    "and": "ənd", "from": "frəm", "as": "əz", "at": "ət",
}  # fmt: skip


@dataclass
class _Seg:
    ipa: str
    vowel: bool
    stress: int = 0  # 0 none, 1 primary, 2 secondary


@dataclass
class Lookup:
    ipa: str | None
    ambiguous: bool = False


@cache
def _dictionary() -> dict[str, list[list[str]]]:
    text = (files("cmudict") / "data" / "cmudict.dict").read_text(encoding="utf-8")
    entries: dict[str, list[list[str]]] = {}
    for line in text.splitlines():
        word, *phones = line.split("#")[0].split()
        entries.setdefault(word.split("(")[0], []).append(phones)
    return entries


def _segments(phones: list[str]) -> list[_Seg]:
    segs: list[_Seg] = []
    for index, phone in enumerate(phones):
        base, stress = phone.rstrip("012"), int(phone[-1]) if phone[-1].isdigit() else 0
        if base in _CONSONANTS:
            segs.append(_Seg(_CONSONANTS[base], vowel=False))
            continue
        before_r = index + 1 < len(phones) and phones[index + 1] == "R"
        if base == "ER":
            # ɜːr / ər: the r is a consonant, so it can start the next
            # syllable (garage ɡəˈrɑːʒ, hurry ˈhɜːri).
            segs.append(_Seg(_VOWELS["ER"][0 if stress else 1], vowel=True, stress=stress))
            segs.append(_Seg("r", vowel=False))
        elif base in ("AY", "AW") and before_r:
            # tyre T AY1 R → ˈtaɪər
            segs.append(_Seg(_VOWELS[base][0], vowel=True, stress=stress))
            segs.append(_Seg("ə", vowel=True))
        elif base in _BEFORE_R and before_r:
            segs.append(_Seg(_BEFORE_R[base], vowel=True, stress=stress))
        else:
            segs.append(_Seg(base, vowel=True, stress=stress))
    return segs


def _vowel_symbols(segs: list[_Seg]) -> None:
    """Resolve ARPABET vowel names to IPA, after stress is final."""
    for index, seg in enumerate(segs):
        if not seg.vowel or seg.ipa not in _VOWELS:
            continue
        stressed, unstressed = _VOWELS[seg.ipa]
        if seg.ipa == "UW" and not seg.stress:
            followed_by_vowel = index + 1 < len(segs) and segs[index + 1].vowel
            seg.ipa = "u" if followed_by_vowel else "uː"
        else:
            seg.ipa = stressed if seg.stress else unstressed


def _primary_index(phones: list[str]) -> int | None:
    """Which vowel (by order) carries the main stress: the last "1"."""
    vowels = [p for p in phones if p[-1].isdigit()]
    ones = [i for i, p in enumerate(vowels) if p.endswith("1")]
    return ones[-1] if ones else None


def _render_word(phones: list[str], mark_single_syllable: bool) -> tuple[str, int]:
    """IPA for one word; also returns its number of syllables."""
    segs = _segments(phones)
    vowels = [seg for seg in segs if seg.vowel]
    primary = _primary_index(phones)
    seen_primary = False
    for position, seg in enumerate(vowels):
        if position == primary:
            seg.stress, seen_primary = 1, True
        elif seg.stress:
            # NAmE marks secondary stress only before the main stress.
            seg.stress = 0 if seen_primary else 2
    _vowel_symbols(segs)
    # Counted before a final ə becomes a syllabic n/l, which is still a syllable.
    syllables = sum(1 for seg in segs if seg.vowel)

    # Syllabic n/l at the end of the word.
    if len(segs) >= 3 and segs[-2].ipa == "ə" and not segs[-2].stress and not segs[-1].vowel:
        last, before = segs[-1].ipa, segs[-3]
        n_ok = (
            last == "n"
            and not before.vowel
            and before.ipa in _SYLLABIC_N_AFTER
            and not (before.ipa == "d" and len(segs) >= 4 and segs[-4].ipa == "n")
        )
        l_ok = last == "l" and not before.vowel and before.ipa not in _NOT_SYLLABIC_L_AFTER
        if n_ok or l_ok:
            del segs[-2]

    marks: dict[int, str] = {}
    if syllables > 1 or mark_single_syllable:
        for index, seg in enumerate(segs):
            if not seg.vowel or not seg.stress:
                continue
            start = index
            while start > 0 and not segs[start - 1].vowel:
                start -= 1
            cluster = [s.ipa for s in segs[start:index]]
            onset = 0
            for size in range(len(cluster), 0, -1):
                if tuple(cluster[-size:]) in _ONSETS:
                    onset = size
                    break
            marks[index - onset] = "ˈ" if seg.stress == 1 else "ˌ"
    text = "".join(marks.get(i, "") + seg.ipa for i, seg in enumerate(segs))
    return text, syllables


def arpabet_to_ipa(phones: list[str]) -> str:
    """Convert one CMUdict entry (e.g. ["Z", "EH1", "L", "AH0", "S"])."""
    return _render_word(phones, mark_single_syllable=False)[0]


def _lookup_word(word: str) -> Lookup:
    entries = _dictionary().get(word)
    if not entries:
        return Lookup(None)
    # Entries that put the main stress on different syllables are
    # different words to a learner (REsearch / reSEARCH): don't guess.
    if len({_primary_index(entry) for entry in entries}) > 1:
        return Lookup(None, ambiguous=True)
    return Lookup(" ".join(entries[0]))


def _lookup_expression(english: str) -> Lookup:
    words = re.findall(r"[a-z][a-z'.-]*", english.strip().casefold())
    if not words:
        return Lookup(None)
    if len(words) == 1:
        found = _lookup_word(words[0])
        return Lookup(arpabet_to_ipa(found.ipa.split()), False) if found.ipa else found

    content = [i for i, w in enumerate(words) if w not in _WEAK_FORMS]
    last_content = content[-1] if content else len(words) - 1
    parts = []
    for index, word in enumerate(words):
        if index != last_content and word in _WEAK_FORMS:
            parts.append(_WEAK_FORMS[word])
            continue
        found = _lookup_word(word)
        if found.ipa is None:
            return found
        ipa, _syllables = _render_word(found.ipa.split(), mark_single_syllable=True)
        if index != last_content:
            # Only the last content word keeps the main stress.
            ipa = ipa.replace("ˈ", "ˌ")
        parts.append(ipa)
    return Lookup(" ".join(parts))


def lookup_american_ipa(english: str, variants: list[str] = ()) -> Lookup:
    """American IPA for *english*, or for the first of its spelling
    *variants* the dictionary knows (epitomise → epitomize). ipa is None
    when no spelling is in the dictionary, or when it is ambiguous."""
    for candidate in [english, *variants]:
        result = _lookup_expression(candidate)
        if result.ipa is not None or result.ambiguous:
            return result
    return Lookup(None)
