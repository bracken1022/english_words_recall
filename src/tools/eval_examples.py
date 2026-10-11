"""Evaluate example sentences against a reviewed word set (spec 021,
research R8): `python -m src.tools.eval_examples [--sample 50]`.

Every fixture word goes through what a learner would get: the local model
writes an example (request_example), validate_example() checks it, and an
invalid one is retried once, as ExampleService does. The tool prints the
automatic pass rate, the rejection reasons and the generation times, and
writes REVIEW.md, a table for a person to tick: natural, correct and in
the recorded meaning (the SC-002 gate is at least 95% ticked and 0 marked
unsafe). It needs a running Ollama, so pytest does not run it. Exit
status: 0 when the automatic checks pass, 1 when not, 2 when the local AI
is unavailable."""

import argparse
import statistics
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

import yaml

from src.services.example_client import request_example, validate_example
from src.services.examples import ATTEMPTS
from src.services.llm_client import DEFAULT_MODEL

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIXTURE = ROOT / "tests/fixtures/example_eval.yml"

VALID_TARGET = 0.95  # enough valid examples to review for SC-002
SLOW_SECONDS = 5.0  # SC-001: a first example within 5 seconds


class Unavailable(Exception):
    pass


def _reason(reason: str) -> str:
    # "23 words" and "2 words" are the same problem.
    return "wrong length" if reason.endswith(" words") else reason


def _generate(entry: dict, base_url: str, model: str, rejected: Counter) -> dict | None:
    for _ in range(ATTEMPTS):
        reply = request_example(entry["english"], entry["chinese"], entry.get("pos", []), base_url, model)
        if reply.outcome == "unavailable":
            raise Unavailable(entry["english"])
        if reply.outcome != "ok":
            rejected[f"bad reply ({reply.detail})"] += 1
            continue
        ok, reason = validate_example(entry["english"], reply.sentence, reply.translation)
        if ok:
            return {"sentence": reply.sentence, "translation": reply.translation}
        rejected[_reason(reason)] += 1
    return None


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def write_review(path: Path, rows: list[tuple[dict, dict | None]], model: str) -> None:
    lines = [
        "# Example sentences: review",
        "",
        f"Model `{model}`, {datetime.now().astimezone():%Y-%m-%d %H:%M}. Spec 021, SC-002.",
        "",
        "Tick **OK** when the sentence is natural, correct English, and uses the",
        "word in the meaning shown, with a translation that matches. Tick",
        "**Unsafe** for anything unsuitable for a family. The release gate is at",
        "least 95% OK and 0 unsafe.",
        "",
        "| # | Word | POS | Meaning | Sentence | Translation | OK | Unsafe |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for number, (entry, example) in enumerate(rows, 1):
        pos = ", ".join(entry.get("pos", []))
        if example:
            sentence, translation = _cell(example["sentence"]), _cell(example["translation"])
        else:
            sentence, translation = "(no valid example)", ""
        lines.append(
            f"| {number} | {_cell(entry['english'])} | {pos} | {_cell(entry['chinese'])} "
            f"| {sentence} | {translation} | [ ] | [ ] |"
        )
    lines += ["", "OK: __ / " + str(len(rows)) + "    Unsafe: __", ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def evaluate(words: list[dict], base_url: str, model: str, out_dir: Path, out=None) -> bool:
    out = out or sys.stdout
    rejected: Counter = Counter()
    rows, times = [], []
    for entry in words:
        started = time.monotonic()
        example = _generate(entry, base_url, model, rejected)
        times.append(time.monotonic() - started)
        rows.append((entry, example))
        if example is None:
            print(f"  NONE    {entry['english']}", file=out)

    review = out_dir / "REVIEW.md"
    write_review(review, rows, model)

    total = len(words)
    valid = sum(1 for _, example in rows if example)
    rate = valid / total if total else 1
    slow = sum(1 for t in times if t > SLOW_SECONDS)
    reasons = ", ".join(f"{reason}: {n}" for reason, n in rejected.most_common()) or "none"
    report = [
        "",
        f"Valid examples: {valid}/{total} ({rate:.0%}, target ≥ {VALID_TARGET:.0%})",
        f"Rejected attempts: {sum(rejected.values())} ({reasons})",
    ]
    if times:
        report.append(
            f"Time per word: median {statistics.median(times):.1f} s, max {max(times):.1f} s, "
            f"{slow} over {SLOW_SECONDS:.0f} s"
        )
    report.append(f"Review: {review}")
    print("\n".join(report), file=out)
    passed = rate >= VALID_TARGET
    print(
        "PASS (automatic checks) — now tick REVIEW.md" if passed else "FAIL: too few valid examples",
        file=out,
    )
    return passed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m src.tools.eval_examples",
        description="Generate example sentences for the reviewed word set (spec 021).",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--ollama-url", default="http://localhost:11434")
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--sample", type=int, default=None, help="use only the first N words")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="folder for REVIEW.md (default: backups/examples-<timestamp>/)",
    )
    args = parser.parse_args(argv)

    words = yaml.safe_load(args.fixture.read_text(encoding="utf-8")).get("words", [])
    if args.sample is not None:
        words = words[: args.sample]
    out_dir = args.out or ROOT / "backups" / f"examples-{datetime.now().astimezone():%Y%m%d-%H%M%S}"
    print(f"Evaluating {args.model} at {args.ollama_url} on {len(words)} words")
    try:
        passed = evaluate(words, args.ollama_url, args.model, out_dir)
    except Unavailable:
        print("Local AI unavailable — start Ollama and try again.", file=sys.stderr)
        return 2
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
