"""Measure automatic word corrections (spec 023, research R10):
`python -m src.tools.eval_corrections tests/fixtures/word_check_cases.yml`.

Each case is checked with Qwen exactly as practice would check it
(word_check.check_word, the case's dialect), without saving anything. A
known error counts as fixed when its wrong field now fits the accepted
values (SC-001, target at least 90%); a right word counts as made worse
when any field leaves them (SC-002, target at most 5%). A failed request
leaves a word as it was: not fixed, not worse.

Needs DASHSCOPE_API_KEY, so pytest does not run it on the real service.
Exit status: 0 when both targets pass, 1 when not, 2 without a key."""

import argparse
import sys
from collections import Counter
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path

import yaml

from src.lib.ipa import normalize_ipa
from src.lib.pos import normalize_pos
from src.services import word_check
from src.services.qwen_client import QwenConfig, QwenError
from src.services.word_check import WordCheck

FIXED_TARGET = 0.90  # SC-001
WORSE_LIMIT = 0.05  # SC-002


@dataclass(frozen=True)
class Case:
    kind: str  # "correct" or "known_error"
    error: str | None  # the wrong field of a known error
    english: str
    dialect: str
    sent: dict
    accepted: dict


def load_cases(path: Path) -> list[Case]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return [
        Case(
            kind=entry["kind"],
            error=entry.get("error"),
            english=str(entry["english"]),
            dialect=entry["dialect"],
            sent=entry["sent"],
            accepted=entry["accepted"],
        )
        for entry in data.get("cases", [])
    ]


def as_check(values: dict) -> WordCheck:
    return WordCheck(values.get("ipa"), values.get("chinese") or "", list(values.get("pos") or []))


def wrong_fields(answer: WordCheck, case: Case) -> list[str]:
    """The fields of *answer* that leave the case's accepted values."""
    accepted = case.accepted
    wrong = []
    ipa, _ = normalize_ipa(answer.ipa)
    if ipa not in [normalize_ipa(i)[0] for i in accepted["ipa"]]:
        wrong.append("ipa")
    if not any(core in answer.chinese for core in accepted["chinese_any"]):
        wrong.append("chinese")
    labels = set(normalize_pos(list(answer.pos))[0] or [])
    allowed = set(accepted["pos"]) | set(accepted.get("pos_ok") or [])
    if not labels or not labels <= allowed or not labels & set(accepted["pos"]):
        wrong.append("pos")
    return wrong


@dataclass
class Report:
    fixed: int = 0
    errors: int = 0
    worse: int = 0
    correct: int = 0
    failures: Counter = field(default_factory=Counter)
    worsened: list[str] = field(default_factory=list)
    unfixed: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        fixed_ok = self.errors == 0 or self.fixed / self.errors >= FIXED_TARGET
        worse_ok = self.correct == 0 or self.worse / self.correct <= WORSE_LIMIT
        return fixed_ok and worse_ok


def _pct(part: int, whole: int) -> str:
    return f"{part}/{whole} ({part / whole:.0%})" if whole else "0/0"


def evaluate(cases: list[Case], check, out=None) -> Report:
    """*check* (english, ipa, chinese, pos, dialect) -> WordCheck."""
    out = out or sys.stdout
    report = Report()
    for case in cases:
        sent = as_check(case.sent)
        try:
            answer = check(case.english, sent.ipa, sent.chinese, list(sent.pos), case.dialect)
        except QwenError as exc:
            report.failures[exc.code] += 1
            answer = sent  # left as it was
        wrong = wrong_fields(answer, case)
        if case.kind == "known_error":
            report.errors += 1
            if case.error in wrong:
                report.unfixed.append(f"{case.english} ({case.error})")
            else:
                report.fixed += 1
        else:
            report.correct += 1
            if wrong:
                report.worse += 1
                report.worsened.append(f"{case.english} ({', '.join(wrong)})")

    print(
        f"Errors fixed: {_pct(report.fixed, report.errors)} (target ≥ {FIXED_TARGET:.0%})", file=out
    )
    print(
        f"Right words made worse: {_pct(report.worse, report.correct)} (target ≤ {WORSE_LIMIT:.0%})",
        file=out,
    )
    if report.failures:
        failed = ", ".join(f"{code} {n}" for code, n in sorted(report.failures.items()))
        print(f"Failed requests: {failed}", file=out)
    if report.unfixed:
        print("Not fixed: " + "; ".join(report.unfixed), file=out)
    if report.worsened:
        print("Made worse: " + "; ".join(report.worsened), file=out)
    print("PASS" if report.passed else "FAIL", file=out)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m src.tools.eval_corrections",
        description="Measure Qwen word corrections on a reviewed fixture (spec 023).",
    )
    parser.add_argument("fixture", type=Path, help="e.g. tests/fixtures/word_check_cases.yml")
    args = parser.parse_args(argv)
    config = QwenConfig.from_env()
    if config is None:
        print("Set DASHSCOPE_API_KEY (and optionally QWEN_BASE_URL, QWEN_MODEL).", file=sys.stderr)
        return 2
    print(f"Model: {config.model}")
    report = evaluate(load_cases(args.fixture), partial(word_check.check_word, config))
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
