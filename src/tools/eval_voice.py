"""Measure voice recognition for sentence recall (spec 022, research R6):
`python -m src.tools.eval_voice <folder> [--model base|small]`.

The folder holds recordings plus `sentences.yml`, mapping each file name
to the sentence read aloud. Each clip goes through what a learner's
recording goes through (speech_client.transcribe), and the text is
compared with the sentence using the same word_diff the learner sees.
Word accuracy is the share of sentence words marked "same". The tool
prints accuracy, the words missed per clip and the time per clip.

The recordings are made by the operator for this check (not learner
data) and belong outside the repo, under backups/. Needs the `voice`
extra, so pytest does not run it on real audio. Exit status: 0 when
SC-002 (≥ 90% of words) and SC-001 (every clip under 3 s) pass, 1 when
not, 2 when the recogniser is unavailable."""

import argparse
import statistics
import sys
import time
from pathlib import Path

import yaml

from src.lib.word_diff import compare
from src.services import speech_client

ACCURACY_TARGET = 0.90  # SC-002
SLOW_SECONDS = 3.0  # SC-001


class Unavailable(Exception):
    pass


def _score(heard: str, sentence: str) -> tuple[int, int, list[str]]:
    """(words right, words in the sentence, words missed)."""
    comparison = compare(heard, sentence)
    if comparison is None:
        words = sentence.split()
        return 0, len(words), words
    missed = [m.word for m in comparison.sentence if m.status == "missing"]
    return len(comparison.sentence) - len(missed), len(comparison.sentence), missed


def evaluate(folder: Path, out=None) -> bool:
    out = out or sys.stdout
    sentences = yaml.safe_load((folder / "sentences.yml").read_text(encoding="utf-8")) or {}
    right = total = 0
    times: list[float] = []
    missing_clips = 0
    for name, sentence in sentences.items():
        clip = folder / name
        if not clip.exists():
            print(f"  MISSING {name}", file=out)
            missing_clips += 1
            continue
        audio = clip.read_bytes()
        started = time.monotonic()
        result = speech_client.transcribe(audio)
        times.append(time.monotonic() - started)
        if result.outcome == "unavailable":
            raise Unavailable(name)
        n_right, n_words, missed = _score(result.text or "", sentence)
        right += n_right
        total += n_words
        if missed:
            print(f"  {name}: heard {result.text!r}; missed {', '.join(missed)}", file=out)

    accuracy = right / total if total else 0.0
    slow = sum(1 for t in times if t > SLOW_SECONDS)
    lines = ["", f"Word accuracy: {right}/{total} ({accuracy:.0%}, target ≥ {ACCURACY_TARGET:.0%})"]
    if times:
        lines.append(
            f"Time per clip: median {statistics.median(times):.1f} s, max {max(times):.1f} s, "
            f"{slow} over {SLOW_SECONDS:.0f} s"
        )
    print("\n".join(lines), file=out)
    passed = accuracy >= ACCURACY_TARGET and slow == 0 and missing_clips == 0 and total > 0
    print("PASS" if passed else "FAIL", file=out)
    return passed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m src.tools.eval_voice",
        description="Measure local speech recognition on recorded sentences (spec 022).",
    )
    parser.add_argument("folder", type=Path, help="recordings plus sentences.yml")
    parser.add_argument("--model", default=None, help="Whisper model size (default: base)")
    args = parser.parse_args(argv)

    if args.model:
        speech_client.configure(args.model)
    if not speech_client.is_available():
        print("Voice is not installed — pip install -e '.[voice]'.", file=sys.stderr)
        return 2
    if not (args.folder / "sentences.yml").is_file():
        print(f"No sentences.yml in {args.folder} (file name -> sentence).", file=sys.stderr)
        return 1
    print(f"Evaluating Whisper {args.model or speech_client.model_size()} on {args.folder}")
    try:
        passed = evaluate(args.folder)
    except Unavailable:
        print("Voice recognition is unavailable — check the voice install.", file=sys.stderr)
        return 2
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
