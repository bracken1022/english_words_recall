"""Fill `ipa:` lines into vocabulary files from a reviewed mapping (spec 017,
contracts/add-ipa-tool-contract.md).

    python -m src.tools.add_ipa --mapping MAPPING.tsv [--backup-root backups] [--dry-run] FILE...

Every mapped value is checked as British IPA before anything is written.
Each changed file is backed up, gets only new `ipa:` lines (inserted after
the block's `english:` line, as a text edit), and is reloaded to prove
nothing else changed; on any mismatch the backup is restored."""

import argparse
import os
import random
import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import yaml

from src.lib.ipa import check_british_ipa, display_ipa, normalize_ipa
from src.lib.markdown_blocks import _BlockLoader, parse_blocks
from src.models.vocabulary_item import VocabularyItem, VocabularyItemError

SPOT_CHECK_SIZE = 30


@dataclass
class MappingEntry:
    ipa: str | None
    note: str


@dataclass
class FileResult:
    path: Path
    new_text: str
    filled: list[tuple[str, str, str]] = field(default_factory=list)
    already: list[str] = field(default_factory=list)
    empty: list[tuple[str, str]] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)


def _read_mapping(path: Path) -> tuple[dict[tuple[str, str], MappingEntry], list[str]]:
    mapping: dict[tuple[str, str], MappingEntry] = {}
    errors: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t") + ["", ""]
        file, english, raw_ipa, note = (p.strip() for p in parts[:4])
        ipa = None
        if raw_ipa:
            ipa, problem = normalize_ipa(raw_ipa)
            problems = [problem] if problem else check_british_ipa(ipa)
            for message in problems:
                errors.append(f"{file}: {english}: {message}")
        mapping[(file, english)] = MappingEntry(ipa=ipa, note=note)
    return mapping, errors


def _english_of(line: str) -> str | None:
    try:
        value = yaml.load(line, Loader=_BlockLoader)
    except yaml.YAMLError:
        return None
    if isinstance(value, dict) and isinstance(value.get("english"), str):
        return value["english"]
    return None


def _plan(path: Path, key: str, mapping: dict) -> FileResult:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    result = FileResult(path=path, new_text=text)
    output: list[str] = []
    inside = False
    for index, line in enumerate(lines):
        output.append(line)
        if line.rstrip("\r\n").strip() == "---":
            inside = not inside
            continue
        if not inside or not line.startswith("english:"):
            continue
        english = _english_of(line)
        if english is None:
            continue
        block_rest = []
        for later in lines[index + 1 :]:
            if later.rstrip("\r\n").strip() == "---":
                break
            block_rest.append(later)
        if any(later.startswith("ipa:") for later in block_rest):
            result.already.append(english)
            continue
        entry = mapping.get((key, english))
        if entry is None:
            result.missing.append(english)
        elif entry.ipa is None:
            result.empty.append((english, entry.note))
        else:
            ending = line[len(line.rstrip("\r\n")) :] or "\n"
            output.append(f"ipa: {entry.ipa}{ending}")
            result.filled.append((english, entry.ipa, entry.note))
    result.new_text = "".join(output)
    return result


def _snapshot(path: Path) -> tuple[list[tuple], int]:
    """(english, chinese, alternates, group) per block, and the warning count."""
    blocks, warnings = parse_blocks(path.read_text(encoding="utf-8"))
    rows = []
    problems = len(warnings)
    for block in blocks:
        try:
            item = VocabularyItem.from_block(block)
        except VocabularyItemError:
            problems += 1
            continue
        if item.ipa_problem:
            problems += 1
        rows.append((item.english, item.chinese, tuple(item.alternates), item.group))
    return rows, problems


def _write_atomic(path: Path, text: str) -> None:
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, suffix=".tmp", delete=False, newline=""
    ) as tmp:
        tmp.write(text)
    shutil.copymode(path, tmp.name)
    os.replace(tmp.name, path)


def _review(results: list[FileResult], stamp: str, totals: str) -> str:
    lines = [f"# IPA fill review — {stamp}", "", totals, "", "## Filled", ""]
    lines += ["| File | Word | IPA | Note |", "|---|---|---|---|"]
    filled = []
    for result in results:
        for english, ipa, note in result.filled:
            filled.append((str(result.path), english, ipa))
            lines.append(f"| {result.path} | {english} | {display_ipa(ipa)} | {note} |")
    lines += ["", "## Left empty", ""]
    empties = [(r.path, e, n) for r in results for e, n in r.empty]
    lines += [
        f"- {path}: **{english}** — {note or 'no reason given'}" for path, english, note in empties
    ]
    if not empties:
        lines.append("None.")
    missing = [(r.path, e) for r in results for e in r.missing]
    if missing:
        lines += ["", "## Missing from mapping", ""]
        lines += [f"- {path}: {english}" for path, english in missing]
    sample = random.Random(stamp).sample(filled, min(SPOT_CHECK_SIZE, len(filled)))
    lines += [
        "",
        f"## Spot check ({len(sample)})",
        "",
        "Check each against a UK learner's dictionary (Cambridge or Oxford) and tick it.",
        "",
        "| Word | IPA | ✓ |",
        "|---|---|---|",
    ]
    lines += [f"| {english} | {display_ipa(ipa)} |  |" for _, english, ipa in sample]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="add_ipa", description=__doc__.splitlines()[0])
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--backup-root", type=Path, default=Path("backups"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("files", nargs="+")
    args = parser.parse_args(argv)

    mapping, errors = _read_mapping(args.mapping)
    if errors:
        for error in errors:
            print(error)
        print(f"{len(errors)} problem(s) in {args.mapping}; no files were changed.")
        return 1

    results = [_plan(Path(key), key, mapping) for key in args.files]
    changed = [r for r in results if r.filled]
    totals = (
        f"filled {sum(len(r.filled) for r in results)} · "
        f"already had {sum(len(r.already) for r in results)} · "
        f"left empty {sum(len(r.empty) for r in results)} · "
        f"missing from mapping {sum(len(r.missing) for r in results)}"
    )
    if args.dry_run:
        print(f"{totals} (dry run, nothing written)")
        return 0
    if not changed:
        print(f"{totals} — nothing to change")
        return 0

    stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    run_dir = args.backup_root / f"ipa-{stamp}"
    before = {}
    for result in changed:
        backup = run_dir / "files" / result.path
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(result.path, backup)
        before[result.path] = _snapshot(result.path)

    for result in changed:
        _write_atomic(result.path, result.new_text)

    mismatched = [r.path for r in changed if _snapshot(r.path) != before[r.path]]
    if mismatched:
        for result in changed:
            shutil.copy2(run_dir / "files" / result.path, result.path)
        for path in mismatched:
            print(f"{path}: content changed beyond the ipa lines — restored from backup")
        return 1

    shutil.copy2(args.mapping, run_dir / "mapping.tsv")
    review = run_dir / "REVIEW.md"
    review.write_text(_review(results, stamp, totals), encoding="utf-8")
    print(f"{totals} — review: {review}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
