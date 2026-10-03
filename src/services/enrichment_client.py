"""Local-model enrichment of one uploaded word (spec 018,
contracts/enrichment-llm-contract.md).

request_enrichment() asks the same local Ollama model used for sentence
review for a word's concise Chinese meaning and spelling variants. (Its
IPA proved unreliable — eval-report.md — so pronunciations come from the
offline dictionary in src/lib/us_pronunciation.py instead.) The reply is
untrusted data only: the model never decides the English text, list or
group names, file paths, workflow state or what is saved (FR-006). Only
the two schema keys are read, and every failure is returned as an
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


@dataclass
class EnrichmentReply:
    outcome: str  # "ok", "unavailable" or "bad_reply"
    chinese: str | None = None
    alternates: list[str] = field(default_factory=list)
    detail: str | None = None


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
    if (
        data is None
        or not isinstance(alternates, list)
        or not all(isinstance(a, str) for a in alternates)
    ):
        return EnrichmentReply(outcome="bad_reply", detail="unusable reply")

    return EnrichmentReply(outcome="ok", chinese=data["chinese"], alternates=list(alternates))
