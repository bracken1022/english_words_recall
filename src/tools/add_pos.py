"""Fill `pos:` lines into vocabulary files from a reviewed mapping (spec 019,
contracts/add-pos-tool-contract.md).

    python -m src.tools.add_pos --mapping MAPPING.tsv [--backup-root backups] [--dry-run] FILE...

Every mapped value is checked as a part of speech before anything is
written. Each changed file is backed up, gets only new `pos:` lines
(inserted after the block's `ipa:` line, or after `english:`, as a text
edit), and is reloaded to prove nothing else changed; on any mismatch
every changed file is restored. Built like spec 017's add_ipa."""

import argparse
import random
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from src.lib.markdown_blocks import parse_blocks
from src.lib.pos import display_pos, normalize_pos
from src.models.vocabulary_item import VocabularyItem, VocabularyItemError
from src.tools.add_ipa import SPOT_CHECK_SIZE, _english_of, _write_atomic


@dataclass
class MappingEntry:
    pos: list[str] | None
    note: str


@dataclass
class FileResult:
    path: Path
    new_text: str
    filled: list[tuple[str, list[str], str]] = field(default_factory=list)
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
        file, english, raw_pos, note = (p.strip() for p in parts[:4])
        pos = None
        if raw_pos:
            pos, problem = normalize_pos(raw_pos)
            if problem:
                errors.append(f"{file}: {english}: {problem}")
        mapping[(file, english)] = MappingEntry(pos=pos, note=note)
    return mapping, errors


def _blocks(lines: list[str]) -> list[tuple[int, int]]:
    """(first, last) line indexes of each block's body, between its `---`."""
    spans, start = [], None
    for index, line in enumerate(lines):
        if line.rstrip("\r\n").strip() == "---":
            if start is None:
                start = index + 1
            else:
                spans.append((start, index - 1))
                start = None
    return spans


def _plan(path: Path, key: str, mapping: dict) -> FileResult:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    result = FileResult(path=path, new_text=text)
    inserts: dict[int, str] = {}  # line index -> text inserted after it
    for first, last in _blocks(lines):
        body = range(first, last + 1)
        english_at = next((i for i in body if lines[i].startswith("english:")), None)
        english = _english_of(lines[english_at]) if english_at is not None else None
        if english is None:
            continue
        if any(lines[i].startswith("pos:") for i in body):
            result.already.append(english)
            continue
        entry = mapping.get((key, english))
        if entry is None:
            result.missing.append(english)
        elif entry.pos is None:
            result.empty.append((english, entry.note))
        else:
            anchor = next((i for i in body if lines[i].startswith("ipa:")), english_at)
            ending = lines[anchor][len(lines[anchor].rstrip("\r\n")) :] or "\n"
            inserts[anchor] = f"pos: [{', '.join(entry.pos)}]{ending}"
            result.filled.append((english, entry.pos, entry.note))
    output = []
    for index, line in enumerate(lines):
        output.append(line)
        if index in inserts:
            output.append(inserts[index])
    result.new_text = "".join(output)
    return result


def _snapshot(path: Path) -> tuple[list[tuple], int]:
    """(english, chinese, alternates, group, ipa) per block, and the warning
    count — everything the fill must leave untouched."""
    blocks, warnings = parse_blocks(path.read_text(encoding="utf-8"))
    rows = []
    problems = len(warnings)
    for block in blocks:
        try:
            item = VocabularyItem.from_block(block)
        except VocabularyItemError:
            problems += 1
            continue
        problems += bool(item.ipa_problem) + bool(item.pos_problem)
        rows.append((item.english, item.chinese, tuple(item.alternates), item.group, item.ipa))
    return rows, problems


def _review(results: list[FileResult], stamp: str, totals: str) -> str:
    lines = [f"# Part-of-speech fill review — {stamp}", "", totals, "", "## Filled", ""]
    lines += ["| File | Word | Part of speech | Note |", "|---|---|---|---|"]
    filled = []
    for result in results:
        for english, pos, note in result.filled:
            filled.append((english, pos))
            lines.append(f"| {result.path} | {english} | {display_pos(pos)} | {note} |")
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
        "Check each against a learner's dictionary and the word's meanings, and tick it.",
        "",
        "| Word | Part of speech | ✓ |",
        "|---|---|---|",
    ]
    lines += [f"| {english} | {display_pos(pos)} |  |" for english, pos in sample]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="add_pos", description=__doc__.splitlines()[0])
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
    run_dir = args.backup_root / f"pos-{stamp}"
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
            print(f"{path}: content changed beyond the pos lines — restored from backup")
        return 1

    shutil.copy2(args.mapping, run_dir / "mapping.tsv")
    review = run_dir / "REVIEW.md"
    review.write_text(_review(results, stamp, totals), encoding="utf-8")
    print(f"{totals} — review: {review}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
