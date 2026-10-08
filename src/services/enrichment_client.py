"""Local-model enrichment of one uploaded word (spec 018,
contracts/enrichment-llm-contract.md).

request_enrichment() asks the same local Ollama model used for sentence
review for a word's concise Chinese meaning and spelling variants;
request_pos() then asks, separately, for its parts of speech (spec 019). (Its
IPA proved unreliable — eval-report.md — so pronunciations come from the
offline dictionary in src/lib/us_pronunciation.py instead.) The reply is
untrusted data only: the model never decides the English text, list or
group names, file paths, workflow state or what is saved (FR-006). Only
the schema keys are read, and every failure is returned as an
outcome rather than raised."""

from dataclasses import dataclass, field

from src.services.llm_client import _parse_object_reply, _post_chat

_SYSTEM_PROMPT = (
    "You provide dictionary data for one English word or expression, for a "
    "Chinese-speaking learner. Respond only with the requested JSON object.\n"
    "- chinese: a concise modern Chinese meaning for vocabulary study: at most "
    "4 short meanings, separated by ；, common meanings first. No "
    "part-of-speech labels, no explanations, no example sentences.\n"
    "- alternates: only spelling variants of the same word (British/American "
    "spellings such as colour/color, or hyphenation such as e-mail/email). "
    "Never give synonyms or related words. Usually this is an empty list.\n"
    "Do not change, correct or translate the English word."
)

_RESPONSE_FORMAT = {
    "type": "object",
    "properties": {
        "chinese": {"type": "string"},
        "alternates": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["chinese", "alternates"],
}

_REQUIRED_FIELDS = ("chinese", "alternates")

# Spec 019: part of speech is asked in a second, narrow request that sees
# the meanings. Asking in the same request over-labelled words and cost
# spelling variants (specs/019-part-of-speech/eval-report.md).
_POS_SYSTEM_PROMPT = (
    "You label the part of speech of one English word or expression, as used "
    "in the Chinese meanings you are given. Respond only with the requested "
    "JSON object.\n"
    "- pos: labels from exactly this list: n. v. adj. adv. prep. conj. pron. "
    "det. int. num. phr. v. phr.\n"
    "- Most words have exactly one part of speech. Add another label only if "
    "one of the meanings you were given clearly belongs to that class; never "
    "for other uses of the word that are not among the meanings.\n"
    "- Order the labels as the meanings are ordered.\n"
    "- Use phr. v. for phrasal verbs and phr. for other multi-word expressions."
)

_POS_RESPONSE_FORMAT = {
    "type": "object",
    "properties": {"pos": {"type": "array", "items": {"type": "string"}}},
    "required": ["pos"],
}


@dataclass
class EnrichmentReply:
    outcome: str  # "ok", "unavailable" or "bad_reply"
    chinese: str | None = None
    alternates: list[str] = field(default_factory=list)
    detail: str | None = None
    pos: list[str] = field(default_factory=list)


def _user_prompt(english: str, supplied: dict) -> str:
    prompt = f'English: "{english}"'
    if supplied.get("chinese"):
        # Context for picking alternates; the learner's meaning is kept
        # whatever the model replies (FR-007).
        prompt += f'\nMeaning: "{supplied["chinese"]}"'
    return prompt


def request_enrichment(
    english: str,
    supplied: dict,
    base_url: str,
    model: str,
    timeout: float = 60.0,
) -> EnrichmentReply:
    payload = {
        "model": model,
        "stream": False,
        "think": False,
        "format": _RESPONSE_FORMAT,
        "options": {"temperature": 0},
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _user_prompt(english, supplied)},
        ],
    }
    content, failure = _post_chat(base_url, payload, timeout)
    if failure == "unavailable":
        return EnrichmentReply(outcome="unavailable", detail=failure)
    if failure is not None:
        return EnrichmentReply(outcome="bad_reply", detail=failure)

    data = _parse_object_reply(content, _REQUIRED_FIELDS, str_fields=("chinese",))
    alternates = data.get("alternates") if data else None
    if data is None or not _is_word_list(alternates):
        return EnrichmentReply(outcome="bad_reply", detail="unusable reply")

    return EnrichmentReply(outcome="ok", chinese=data["chinese"], alternates=list(alternates))


def request_pos(
    english: str,
    chinese: str,
    base_url: str,
    model: str,
    timeout: float = 60.0,
) -> EnrichmentReply:
    """Spec 019: the part-of-speech labels for *english* as used in its
    *chinese* meanings; outcome as for request_enrichment, labels in pos
    (still untrusted: validate_item normalises them)."""
    payload = {
        "model": model,
        "stream": False,
        "think": False,
        "format": _POS_RESPONSE_FORMAT,
        "options": {"temperature": 0},
        "messages": [
            {"role": "system", "content": _POS_SYSTEM_PROMPT},
            {"role": "user", "content": f'English: "{english}"\nMeaning: "{chinese}"'},
        ],
    }
    content, failure = _post_chat(base_url, payload, timeout)
    if failure == "unavailable":
        return EnrichmentReply(outcome="unavailable", detail=failure)
    if failure is not None:
        return EnrichmentReply(outcome="bad_reply", detail=failure)
    data = _parse_object_reply(content, ("pos",))
    if data is None or not _is_word_list(data["pos"]):
        return EnrichmentReply(outcome="bad_reply", detail="unusable reply")
    return EnrichmentReply(outcome="ok", pos=list(data["pos"]))


def _is_word_list(value) -> bool:
    return isinstance(value, list) and all(isinstance(v, str) for v in value)
