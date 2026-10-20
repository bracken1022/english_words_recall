"""Check one vocabulary word with Qwen: its American IPA, Chinese meaning
and parts of speech, corrected where they are wrong.

This is only the task (prompt and strict validation of the reply); the
transport is src/services/qwen_client.py. The reply is untrusted data: the
English word is never changed, every field is normalised by the same rules
as hand-written lists, and anything that doesn't fit is rejected rather
than guessed.
"""

from dataclasses import dataclass

from src.lib.content_filter import is_clean
from src.lib.ipa import normalize_ipa
from src.lib.pos import POS_LABELS, normalize_pos
from src.services.qwen_client import QwenConfig, complete_json

MAX_CHINESE_LENGTH = 60

SYSTEM_PROMPT = (
    "You check dictionary data for one English word or expression, for a "
    "Chinese-speaking learner. You are given the word and its current "
    "pronunciation, Chinese meaning and parts of speech; some may be wrong "
    "or missing. Respond only with a JSON object with exactly these keys:\n"
    '- "ipa": the General American IPA, without slashes, with stress marks '
    "(ˈ ˌ).\n"
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
    ipa: str
    chinese: str
    pos: list[str]


def user_text(english: str, ipa: str | None, chinese: str | None, pos: list[str]) -> str:
    return (
        f'English: "{english}"\n'
        f'Current IPA: "{ipa or ""}"\n'
        f'Current Chinese: "{chinese or ""}"\n'
        f'Current parts of speech: "{" ".join(pos)}"'
    )


def validate(data: dict) -> WordCheck:
    """The checked values, or ValueError when the reply doesn't fit."""
    if set(data) != _KEYS:
        raise ValueError("unexpected keys")

    ipa, problem = normalize_ipa(data["ipa"])
    if ipa is None or problem:
        raise ValueError("bad ipa")

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
) -> WordCheck:
    """Qwen's checked values for one word. Raises QwenError on any failure."""
    return complete_json(config, SYSTEM_PROMPT, user_text(english, ipa, chinese, pos), validate)
