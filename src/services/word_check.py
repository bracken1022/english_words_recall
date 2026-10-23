"""Check one vocabulary word with Qwen: its IPA (British or American, the
list's dialect), Chinese meaning and parts of speech, corrected where they
are wrong.

This is only the task (prompt and strict validation of the reply); the
transport is src/services/qwen_client.py. The reply is untrusted data: the
English word is never changed, every field is normalised by the same rules
as hand-written lists, and anything that doesn't fit is rejected rather
than guessed. Only the five word lines of user_text() are sent (spec 023
FR-013).
"""

from dataclasses import dataclass
from functools import partial

from src.lib.content_filter import is_clean
from src.lib.ipa import check_american_ipa, check_british_ipa, is_heteronym, normalize_ipa
from src.lib.pos import POS_LABELS, normalize_pos
from src.services.qwen_client import QwenConfig, complete_json

MAX_CHINESE_LENGTH = 60
DIALECTS = ("british", "american")

_IPA_RULES = {
    "british": (
        "the British (RP) IPA in the Oxford Learner's Dictionaries style, "
        "without slashes, with stress marks (ˈ ˌ), non-rhotic (ˈteɪlə)"
    ),
    "american": (
        "the American IPA in the Oxford Learner's Dictionaries NAmE style, "
        "without slashes, with stress marks (ˈ ˌ), written with ər, not ɚ "
        "(ˈteɪlər)"
    ),
}
_IPA_CHECKS = {"british": check_british_ipa, "american": check_american_ipa}


def system_prompt(dialect: str) -> str:
    if dialect not in DIALECTS:
        raise ValueError(f"unknown dialect: {dialect!r}")
    return (
        "You check dictionary data for one English word or expression, for a "
        "Chinese-speaking learner. You are given the word and its current "
        "pronunciation, Chinese meaning and parts of speech; some may be wrong "
        "or missing. Respond only with a JSON object with exactly these keys:\n"
        f'- "ipa": {_IPA_RULES[dialect]}. Keep the current IPA if it is correct.\n'
        '- "chinese": a concise modern Chinese meaning: at most 4 short '
        "meanings separated by ；, common meanings first, no part-of-speech "
        "labels, no explanations. Keep the current meaning if it is correct.\n"
        f'- "pos": a list of labels from exactly this set: {" ".join(POS_LABELS)}, '
        "in the order of the meanings; most words have one.\n"
        "Do not change, correct or translate the English word."
    )


_KEYS = {"ipa", "chinese", "pos"}


@dataclass(frozen=True)
class WordCheck:
    ipa: str | None
    chinese: str
    pos: list[str]


def user_text(
    english: str, ipa: str | None, chinese: str | None, pos: list[str], dialect: str
) -> str:
    return (
        f'English: "{english}"\n'
        f"Dialect: {dialect.capitalize()}\n"
        f'Current IPA: "{ipa or ""}"\n'
        f'Current Chinese: "{chinese or ""}"\n'
        f'Current parts of speech: "{" ".join(pos)}"'
    )


def validate(data: dict, dialect: str | None) -> WordCheck:
    """The checked values, or ValueError when the reply doesn't fit.
    *dialect* None skips the dialect's IPA check (heteronyms, whose IPA is
    not used)."""
    if dialect is not None and dialect not in DIALECTS:
        raise ValueError(f"unknown dialect: {dialect!r}")
    if set(data) != _KEYS:
        raise ValueError("unexpected keys")

    ipa, problem = normalize_ipa(data["ipa"])
    if ipa is None or problem:
        raise ValueError("bad ipa")
    if dialect is not None and _IPA_CHECKS[dialect](ipa):
        raise ValueError("ipa not in the dialect")

    chinese = data["chinese"]
    if (
        not isinstance(chinese, str)
        or not chinese.strip()
        or len(chinese.strip()) > MAX_CHINESE_LENGTH
        or not is_clean(chinese)
    ):
        raise ValueError("bad chinese")

    raw_pos = data["pos"]
    if not isinstance(raw_pos, list) or not raw_pos:
        raise ValueError("bad pos")
    pos, problem = normalize_pos(raw_pos)
    if pos is None or problem:
        raise ValueError("bad pos")

    return WordCheck(ipa=ipa, chinese=chinese.strip(), pos=pos)


def check_word(
    config: QwenConfig | None,
    english: str,
    ipa: str | None,
    chinese: str | None,
    pos: list[str],
    dialect: str,
) -> WordCheck:
    """Qwen's checked values for one word. Raises QwenError on any failure.
    A heteronym keeps its current IPA: the right one depends on the
    meaning (spec 023 research R3)."""
    heteronym = is_heteronym(english)
    result = complete_json(
        config,
        system_prompt(dialect),
        user_text(english, ipa, chinese, pos, dialect),
        partial(validate, dialect=None if heteronym else dialect),
    )
    if heteronym:
        return WordCheck(ipa=ipa, chinese=result.chinese, pos=result.pos)
    return result
