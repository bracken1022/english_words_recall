"""A family-safety check for generated example sentences (spec 021,
Constitution II). Examples are written by the local model and shown
without a person reading them first, so anything containing a word from
this reviewed blocklist is discarded rather than shown.

English entries match whole words (so "class" never trips on "ass");
the word being studied is exempt, so "torture" can have an example;
Chinese entries match anywhere in the text."""

import re

BLOCKLIST = frozenset(
    {
        # profanity and insults
        "fuck", "fucking", "fucked", "shit", "shitty", "bitch", "bastard", "asshole",
        "ass", "damn", "dick", "cock", "pussy", "cunt", "slut", "whore", "prick",
        "wanker", "bollocks", "retard", "retarded", "moron",
        # sexual content
        "sex", "sexy", "porn", "porno", "pornography", "nude", "naked", "orgasm",
        "erotic", "rape", "raped", "rapist", "prostitute", "stripper",
        # drugs and graphic violence
        "cocaine", "heroin", "meth", "overdose", "suicide", "behead", "massacre",
        "torture", "murder", "murdered",
        # slurs
        "nigger", "nigga", "faggot", "fag", "chink", "spic", "kike", "tranny",
        # Chinese
        "他妈的", "操你", "傻逼", "妈的", "婊子", "色情", "强奸", "自杀", "毒品", "裸体",
    }
)  # fmt: skip

_WORD = re.compile(r"[a-z]+")
_ENGLISH = {w for w in BLOCKLIST if w.isascii()}
_CHINESE = [w for w in BLOCKLIST if not w.isascii()]


def is_clean(text: str, allow: set[str] | frozenset[str] = frozenset()) -> bool:
    """True when *text* has no blocklisted word. Words in *allow* (the
    vocabulary word being studied and its forms, e.g. "torture") are
    exempt: the learner chose to learn them."""
    lowered = text.lower()
    if any(word in _ENGLISH and word not in allow for word in _WORD.findall(lowered)):
        return False
    return not any(entry in text for entry in _CHINESE)
