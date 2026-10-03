"""Evaluate local-AI enrichment against a reviewed word set (spec 018,
research R10): `python -m src.tools.eval_enrichment`.

Every fixture word goes through the real pipeline — request_enrichment()
on the local model, then validate_item() — and the report measures what a
learner would get: IPA that matches the reviewed transcription or is
flagged for review (never silently wrong), usable Chinese, flagged
heteronyms, no broad synonyms as alternates, and found spelling variants.
It needs a running Ollama, so pytest does not run it. Exit status: 0 when
SC-002/SC-003 are met, 1 when not, 2 when the local AI is unavailable."""

import argparse
import re
import sys
from pathlib import Path

import yaml

from src.lib.ipa import _US_VOWELS, _syllables, check_american_ipa
from src.models.vocabulary_item import VocabularyItem, VocabularyItemError
from src.services.enrichment import ImportItem, validate_item
from src.services.enrichment_client import request_enrichment
from src.services.llm_client import DEFAULT_MODEL

DEFAULT_FIXTURE = Path(__file__).resolve().parents[2] / "tests/fixtures/enrichment_eval.yml"

IPA_TARGET = 0.95  # SC-002: match or flagged
VARIANT_TARGET = 0.90  # SC-003


class Unavailable(Exception):
    pass


def _comparable(ipa: str) -> list[tuple[str, int | None]]:
    """A transcription reduced to what American dictionaries agree on, so
    that convention differences don't count as errors: per word, the
    sounds plus which syllable carries the main stress. Ignored: where
    the stress mark sits in a consonant cluster, secondary stress, the
    flap mark, unstressed ɪ vs ə (vitamin -mɪn/-mən), ɑː vs ɔː (the
    cot-caught merger, coffee), and syllabic n/l vs ən/əl. Consonants,
    full vowels and the stressed syllable must still match."""
    words = []
    for word in ipa.replace("\u032c", "").replace("ˌ", "").split():
        # Syllabic n/l written out as ən/əl (nation ˈneɪʃn = ˈneɪʃən).
        bare = re.sub(r"([^aeiouɪʊəæʌɑɔɜːrˈ])([nl])$", r"\1ə\2", word.replace("ˈ", ""))
        bare = bare.replace("ɔː", "ɑː")
        if _syllables(bare, _US_VOWELS) <= 1:
            words.append((bare, None))
            continue
        stressed = _syllables(word[: word.index("ˈ")], _US_VOWELS) if "ˈ" in word else None
        words.append((re.sub(r"(?<![aeɔo])ɪ(?!r)", "ə", bare), stressed))
    return words


def _enricher(base_url: str, model: str):
    cache: dict[str, ImportItem] = {}

    def enrich(english: str) -> ImportItem:
        if english not in cache:
            item = ImportItem(english=english, position="eval", supplied={"alternates": []})
            reply = request_enrichment(english, item.supplied, base_url, model)
            if reply.outcome == "unavailable":
                raise Unavailable(english)
            if reply.outcome == "ok":
                validate_item(item, reply)
            else:
                item.state, item.error = "failed", f"bad reply ({reply.detail})"
            cache[english] = item
        return cache[english]

    return enrich


def _is_invalid(item: ImportItem) -> bool:
    """Would this enriched item put something invalid into Markdown?"""
    if item.state != "enriched":
        return False
    try:
        VocabularyItem(item.english, item.chinese, list(item.alternates), ipa=item.ipa)
    except VocabularyItemError:
        return True
    return item.ipa is not None and bool(check_american_ipa(item.ipa))


def _pct(part: int, whole: int) -> str:
    return f"{(part / whole if whole else 1):.0%}"


def evaluate(fixture: dict, enrich, out=None) -> bool:
    out = out or sys.stdout
    words = fixture.get("words", [])
    matched = flagged = wrong = chinese_hits = failed = invalid = 0
    for entry in words:
        item = enrich(entry["english"])
        invalid += _is_invalid(item)
        if item.state != "enriched":
            failed += 1
            print(f"  FAILED  {entry['english']}: {item.error}", file=out)
            continue
        if item.ipa is None:
            flagged += 1
            print(f"  review  {entry['english']}: {item.ipa_review}", file=out)
        elif any(
            _comparable(item.ipa) == _comparable(accepted)
            for accepted in [entry["ipa"], *entry.get("ipa_also", [])]
        ):
            matched += 1
        else:
            wrong += 1
            print(f"  WRONG   {entry['english']}: /{item.ipa}/, expected /{entry['ipa']}/", file=out)
        parts = (item.chinese or "").split("；")
        if any(gloss in part for gloss in entry["chinese_any"] for part in parts):
            chinese_hits += 1
        else:
            print(f"  meaning {entry['english']}: {item.chinese}", file=out)

    heteronyms = fixture.get("heteronyms", [])
    heteronyms_flagged = sum(1 for w in heteronyms if enrich(w).ipa is None)

    leaks = []
    for entry in fixture.get("traps", []):
        item = enrich(entry["english"])
        invalid += _is_invalid(item)
        kept = {a.casefold() for a in item.alternates}
        leaks += [(entry["english"], f) for f in entry["forbidden"] if f.casefold() in kept]

    variants = fixture.get("variants", [])
    found = 0
    for entry in variants:
        item = enrich(entry["english"])
        invalid += _is_invalid(item)
        if entry["expected"].casefold() in {a.casefold() for a in item.alternates}:
            found += 1
        else:
            got = ", ".join(item.alternates) or "none"
            print(f"  variant {entry['english']}: expected {entry['expected']}, got {got}", file=out)

    total = len(words)
    ipa_ok = (matched + flagged) / total if total else 1
    variant_recall = found / len(variants) if variants else 1
    tested = total - failed
    report = [
        "",
        (
            f"IPA:            {matched}/{total} match ({_pct(matched, total)}), "
            f"{flagged} flagged, {wrong} wrong and unflagged, {failed} failed "
            f"→ match or flagged {ipa_ok:.0%} (target ≥ {IPA_TARGET:.0%})"
        ),
        (
            f"Chinese:        {chinese_hits}/{tested} hit an accepted meaning "
            f"({_pct(chinese_hits, tested)})"
        ),
        f"Heteronyms:     {heteronyms_flagged}/{len(heteronyms)} flagged",
        f"Synonym traps:  {len(leaks)} leaked (target 0)" + (f": {leaks}" if leaks else ""),
        (
            f"Variants:       {found}/{len(variants)} found ({variant_recall:.0%}, "
            f"target ≥ {VARIANT_TARGET:.0%})"
        ),
        f"Invalid output: {invalid} (target 0)",
    ]
    print("\n".join(report), file=out)
    passed = (
        ipa_ok >= IPA_TARGET
        and wrong == 0
        and not leaks
        and variant_recall >= VARIANT_TARGET
        and invalid == 0
    )
    print("PASS" if passed else "FAIL: SC-002/SC-003 not met", file=out)
    return passed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m src.tools.eval_enrichment",
        description="Measure local-AI enrichment against the reviewed word set (spec 018).",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--ollama-url", default="http://localhost:11434")
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    args = parser.parse_args(argv)

    fixture = yaml.safe_load(args.fixture.read_text(encoding="utf-8"))
    print(f"Evaluating {args.model} at {args.ollama_url} on {args.fixture.name}")
    try:
        passed = evaluate(fixture, _enricher(args.ollama_url, args.model))
    except Unavailable:
        print("Local AI unavailable — start Ollama and try again.", file=sys.stderr)
        return 2
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
