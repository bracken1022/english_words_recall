"""Conservative alternates for enriched uploads (spec 018 FR-011, research R6).

An alternate is an extra answer accepted in recall, so a broad synonym
("arduous" → "difficult") would weaken it. The local model may propose
alternates, but filter_alternates() keeps a proposal only when
is_spelling_variant() proves it is the same word spelled differently
(British/American spelling, hyphenation). Alternates the learner supplied
are their own choice and always kept."""

import re

MAX_ALTERNATES = 5
MAX_ALTERNATE_LENGTH = 64

# Pairs no rewrite rule below can derive. Each pair is reviewed: the two
# spellings must be the same word, never just related ones.
IRREGULAR_VARIANTS = frozenset(
    frozenset(pair)
    for pair in [
        ("tyre", "tire"),
        ("tyres", "tires"),
        ("grey", "gray"),
        ("aluminium", "aluminum"),
        ("plough", "plow"),
        ("kerb", "curb"),
        ("programme", "program"),
        ("programmes", "programs"),
        ("cosy", "cozy"),
        ("mould", "mold"),
        ("sceptic", "skeptic"),
        ("sceptical", "skeptical"),
        ("pyjamas", "pajamas"),
        ("storey", "story"),
        ("moustache", "mustache"),
        ("cheque", "check"),
        ("draught", "draft"),
        ("jewellery", "jewelry"),
        ("manoeuvre", "maneuver"),
        ("judgement", "judgment"),
        ("ageing", "aging"),
        ("fulfil", "fulfill"),
        ("enrol", "enroll"),
        ("instalment", "installment"),
        ("sulphur", "sulfur"),
        ("foetus", "fetus"),
        ("oestrogen", "estrogen"),
    ]
)

# -ence/-ense pairs are only safe for these stems (fence ≠ fense).
_ENCE_STEMS = ("defence", "offence", "licence", "pretence")

# British → American rewrites, applied in order to a lowercased word with
# hyphens and spaces removed. Each needs enough of a stem before the
# ending so short unrelated words (rise/rize, hour/hor) never match.
_REWRITES = [
    (re.compile(r"(?<=\w{3})isation"), "ization"),
    (re.compile(r"(?<=\w{3})is(e|ed|es|er|ers|ing)$"), r"iz\1"),
    (re.compile(r"(?<=\w{2})ys(e|ed|es|er|ers|ing)$"), r"yz\1"),
    (re.compile(r"(?<=\w{3})our(s|ed|ing|ful|ite|ites|able|er|ers)?$"), r"or\1"),
    (re.compile(r"(?<=\w{2})tre(s)?$"), r"ter\1"),
    (re.compile(r"(?<=\w{3})ogue(s)?$"), r"og\1"),
    (re.compile(r"(?<=\w{2}[aeiou])ll(ed|ing|er|ers)$"), r"l\1"),
    # anaemia/anemia, paediatric/pediatric: "ae" between consonants only.
    (re.compile(r"(?<=[b-df-hj-np-tv-z])ae(?=[b-df-hj-np-tv-z])"), "e"),
]


def canonical(word: str) -> str:
    text = word.casefold().replace("-", "").replace(" ", "")
    for stem in _ENCE_STEMS:
        if text.startswith(stem):
            text = stem[:-2] + "se" + text[len(stem) :]
    for pattern, replacement in _REWRITES:
        text = pattern.sub(replacement, text)
    return text


def is_spelling_variant(a: str, b: str) -> bool:
    """True when *a* and *b* are different spellings of the same word."""
    if a.casefold() == b.casefold():
        return False
    if canonical(a) == canonical(b):
        return True
    return frozenset((a.casefold(), b.casefold())) in IRREGULAR_VARIANTS


def filter_alternates(
    english: str, supplied: list[str], proposed: list[str]
) -> tuple[list[str], list[str]]:
    """Return (kept, dropped). *supplied* (the learner's own) come first
    and are kept; *proposed* (the model's) are kept only if they are
    spelling variants of *english*. Duplicates (ignoring case), entries
    equal to *english*, empty or overlong entries are dropped; at most
    MAX_ALTERNATES are kept. *dropped* lists rejected entries in order."""
    kept: list[str] = []
    dropped: list[str] = []
    seen = {english.strip().casefold()}

    def consider(raw, must_be_variant: bool) -> None:
        text = raw.strip() if isinstance(raw, str) else ""
        ok = (
            text
            and len(text) <= MAX_ALTERNATE_LENGTH
            and text.casefold() not in seen
            and len(kept) < MAX_ALTERNATES
            and (not must_be_variant or is_spelling_variant(english.strip(), text))
        )
        if ok:
            kept.append(text)
            seen.add(text.casefold())
        else:
            dropped.append(raw)

    for raw in supplied:
        consider(raw, must_be_variant=False)
    for raw in proposed:
        consider(raw, must_be_variant=True)
    return kept, dropped
