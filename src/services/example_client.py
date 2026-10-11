"""Example sentences from the local model (spec 021, research R3).

request_example() asks the same local Ollama model used for enrichment
for one short, natural sentence using a word in its recorded meaning,
with a Chinese translation. The reply is untrusted: validate_example()
decides whether it may be shown."""

import re
from dataclasses import dataclass

from src.lib.content_filter import is_clean
from src.lib.word_forms import contains_form, inflections
from src.services.llm_client import _parse_object_reply, _post_chat

MAX_WORDS = 20
MIN_WORDS = 3
MAX_TRANSLATION = 60

_SYSTEM_PROMPT = (
    "You write one example sentence for an English word, for a Chinese-speaking "
    "learner. Respond only with the requested JSON object.\n"
    "- sentence: one short, natural, everyday English sentence, at most 20 words, "
    "the kind a native speaker would really say. Use the word in the meaning and "
    "part of speech you are given; inflect it naturally if needed.\n"
    "- translation: a natural Chinese translation of that sentence.\n"
    "- Keep the content suitable for a family learner of any age."
)

_RESPONSE_FORMAT = {
    "type": "object",
    "properties": {"sentence": {"type": "string"}, "translation": {"type": "string"}},
    "required": ["sentence", "translation"],
}

_CJK = re.compile(r"[一-鿿]")
_SENTENCE_END = re.compile(r"[.!?。！？]")


@dataclass
class ExampleReply:
    outcome: str  # "ok", "unavailable" or "bad_reply"
    sentence: str | None = None
    translation: str | None = None
    detail: str | None = None


def request_example(
    english: str,
    chinese: str,
    pos: list[str],
    base_url: str,
    model: str,
    timeout: float = 30.0,
    avoid: str | None = None,
) -> ExampleReply:
    """*avoid* is the word's current example, when asking for a new one."""
    labels = " ".join(pos) if pos else "unknown"
    request = f'English: "{english}"\nMeaning: "{chinese}"\nPart of speech: {labels}'
    if avoid:
        request += f'\nWrite a different sentence from: "{avoid}"'
    payload = {
        "model": model,
        "stream": False,
        "think": False,
        "format": _RESPONSE_FORMAT,
        "options": {"temperature": 0.7},
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": request},
        ],
    }
    content, failure = _post_chat(base_url, payload, timeout)
    if failure == "unavailable":
        return ExampleReply("unavailable", detail=failure)
    if failure is not None:
        return ExampleReply("bad_reply", detail=failure)
    data = _parse_object_reply(content, ("sentence", "translation"), str_fields=("sentence", "translation"))
    if data is None:
        return ExampleReply("bad_reply", detail="unusable reply")
    return ExampleReply("ok", data["sentence"].strip(), data["translation"].strip())


def validate_example(english: str, sentence: str, translation: str) -> tuple[bool, str | None]:
    """(True, None) when the example may be shown, else (False, reason)."""
    if not sentence or "\n" in sentence or "\r" in sentence:
        return False, "not a single line"
    ends = _SENTENCE_END.findall(sentence)
    if len(ends) != 1 or not _SENTENCE_END.match(sentence.rstrip("\"'”’)")[-1:]):
        return False, "not exactly one sentence"
    words = sentence.split()
    if not MIN_WORDS <= len(words) <= MAX_WORDS:
        return False, f"{len(words)} words"
    if not contains_form(sentence, english):
        return False, "doesn't use the word"
    if not translation or not _CJK.search(translation) or len(translation) > MAX_TRANSLATION:
        return False, "translation unusable"
    allow = set().union(*(inflections(w) for w in english.lower().split()))
    if not is_clean(sentence, allow) or not is_clean(translation):
        return False, "not suitable"
    return True, None
