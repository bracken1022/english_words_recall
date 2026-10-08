"""Part-of-speech labels for vocabulary (spec 019, research R2).

A word's `pos` is an ordered list of labels from a fixed set (n., v.,
adj., …), shown before its Chinese meaning. normalize_pos() accepts the
spellings people write by hand (adjective, Adj, 形容词, noun/verb, n. v.)
and returns the labels; anything else is reported, never guessed."""

import re

POS_LABELS = (
    "n.", "v.", "adj.", "adv.", "prep.", "conj.",
    "pron.", "det.", "int.", "num.", "phr. v.", "phr.",
)  # fmt: skip

POS_NAMES = {
    "n.": "noun",
    "v.": "verb",
    "adj.": "adjective",
    "adv.": "adverb",
    "prep.": "preposition",
    "conj.": "conjunction",
    "pron.": "pronoun",
    "det.": "determiner",
    "int.": "interjection",
    "num.": "number",
    "phr. v.": "phrasal verb",
    "phr.": "phrase or idiom",
}

# Abbreviations (matched without their dot), English names, Chinese names.
_ABBREVIATIONS = {
    "n": "n.", "v": "v.", "vt": "v.", "vi": "v.", "a": "adj.", "adj": "adj.",
    "ad": "adv.", "adv": "adv.", "prep": "prep.", "conj": "conj.", "pron": "pron.",
    "det": "det.", "art": "det.", "int": "int.", "interj": "int.", "num": "num.",
    "phr": "phr.",
}  # fmt: skip
_NAMES = {
    "noun": "n.", "verb": "v.", "adjective": "adj.", "adverb": "adv.",
    "preposition": "prep.", "conjunction": "conj.", "pronoun": "pron.",
    "determiner": "det.", "article": "det.", "interjection": "int.",
    "number": "num.", "numeral": "num.", "phrase": "phr.", "idiom": "phr.",
    "名词": "n.", "动词": "v.", "及物动词": "v.", "不及物动词": "v.",
    "形容词": "adj.", "副词": "adv.", "介词": "prep.", "连词": "conj.",
    "代词": "pron.", "限定词": "det.", "冠词": "det.", "感叹词": "int.",
    "数词": "num.", "短语": "phr.", "习语": "phr.",
}  # fmt: skip

# Multi-word labels, protected before splitting on spaces.
_PHRASAL_VERB = re.compile(r"phr\.?\s*v\.?|phrasal\s+verb|短语动词", re.IGNORECASE)
_SPLIT = re.compile(r"[\s,，/;；、]+")
_PV_TOKEN = "\x00pv\x00"

# A parenthesised part-of-speech note inside a meaning: （动词）, (v.).
_NOTE = re.compile(
    r"[（(]\s*(?:"
    + "|".join(
        sorted((re.escape(n) for n in _NAMES), key=len, reverse=True)
        + [r"phr\.?\s*v\.?", r"phrasal\s+verb", r"短语动词"]
        + [rf"{re.escape(a)}\.?" for a in sorted(_ABBREVIATIONS, key=len, reverse=True)]
    )
    + r")\s*[）)]",
    re.IGNORECASE,
)


def _label(token: str) -> str | None:
    if token == _PV_TOKEN:
        return "phr. v."
    key = token.casefold()
    if key in _NAMES:
        return _NAMES[key]
    return _ABBREVIATIONS.get(key.rstrip("."))


def _tokens(text: str) -> list[str]:
    protected = _PHRASAL_VERB.sub(f" {_PV_TOKEN} ", text)
    return [t for t in _SPLIT.split(protected) if t]


def normalize_pos(raw) -> tuple[list[str] | None, str | None]:
    """(labels, None), or (None, problem) when *raw* isn't a part of
    speech. None means no value at all: (None, None)."""
    if raw is None:
        return None, None
    problem = f'pos "{raw}" is not a part of speech'
    if isinstance(raw, str):
        tokens = _tokens(raw)
    elif isinstance(raw, list) and all(isinstance(t, str) for t in raw):
        tokens = [t for item in raw for t in _tokens(item)]
    else:
        return None, problem
    labels: list[str] = []
    for token in tokens:
        label = _label(token)
        if label is None:
            return None, problem
        if label not in labels:
            labels.append(label)
    return (labels, None) if labels else (None, problem)


def is_pos_field(text: str) -> bool:
    """Whether a simple-list field is a part of speech. Stricter than
    normalize_pos: each token must be a dotted abbreviation, an English
    name or a Chinese name, so a short alternate ("n", "a") never is."""
    tokens = _tokens(text.strip())
    if not tokens:
        return False
    for token in tokens:
        if token == _PV_TOKEN:
            continue
        key = token.casefold()
        dotted = key.endswith(".") and key.rstrip(".") in _ABBREVIATIONS
        if not (dotted or key in _NAMES):
            return False
    return True


def strip_pos_notes(text: str) -> str:
    """Remove part-of-speech notes such as "（动词）" from a meaning (FR-008)."""
    kept = []
    for part in text.split("；"):
        stripped = _NOTE.sub("", part).strip()
        # Drop only a part the note filled entirely; keep other empty
        # parts so the meaning checks still see them.
        if stripped or not part.strip():
            kept.append(stripped)
    return "；".join(kept)


def display_pos(labels: list[str]) -> str:
    return " ".join(labels)
