"""Per-account uploaded word lists (spec 016, contracts/upload-formats.md).

parse_upload() turns an uploaded vocabulary Markdown file or simple
"English, Chinese" list into VocabularyItems; WordListStore saves each list
as vocabulary Markdown under <root>/<username>/<name>.md, so an account's
folder is just another vocabulary directory for load_vocabulary()."""

import csv
import json
import os
import re
import shutil
import tempfile
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import yaml

from src.lib.ipa import normalize_ipa
from src.lib.markdown_blocks import _BLOCK_RE, parse_blocks
from src.lib.pos import is_pos_field, normalize_pos
from src.models.account import Account
from src.models.vocabulary_item import VocabularyItem, VocabularyItemError
from src.services.corrections_file import WordValues

MAX_WORDS = 5000
MAX_NAME_LENGTH = 64
SIMPLE_EXTENSIONS = {".csv", ".txt", ".tsv"}
MARKDOWN_EXTENSIONS = {".md", ".markdown"}
HEADER_WORDS = {"english", "word", "英文", "单词"}
DEFAULT_LIST_NAME = "My words"


class UploadFormatError(Exception):
    """The upload can't be used at all (type, encoding, or size)."""


class ListExistsError(Exception):
    """A list with this name (ignoring case) already exists."""

    def __init__(self, name: str):
        super().__init__(name)
        self.name = name


@dataclass
class DraftWord:
    """An uploaded entry that may still be missing its Chinese meaning or
    pronunciation (spec 018, data-model.md); enrichment fills the gaps."""

    english: str
    chinese: str | None
    ipa: str | None
    alternates: list[str]
    position: str
    pos: list[str] = field(default_factory=list)


@dataclass
class ParsedUpload:
    # VocabularyItems by default; DraftWords with require_chinese=False.
    items: list = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


@dataclass
class RemovedEntry:
    """One entry cut from a learner's list file, kept so it can be undone
    exactly (spec 020, data-model.md)."""

    path: Path
    offset: int
    text: str
    file_after: str


@dataclass
class SaveResult:
    name: str
    replaced: bool
    first_list: bool


def _decode(data: bytes) -> str:
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise UploadFormatError("Couldn't read the file's text. Save it as UTF-8 and try again.")


def _split_line(line: str) -> list[str]:
    if "\t" in line:
        fields = next(csv.reader([line], delimiter="\t"))
    else:
        fields = next(csv.reader([line.replace("，", ",")], skipinitialspace=True))
    return [f.strip() for f in fields]


def _is_pronunciation(field_text: str) -> bool:
    return len(field_text) >= 2 and (field_text[0], field_text[-1]) in (("/", "/"), ("[", "]"))


def _split_extras(
    number: int, extras: list[str], skipped: list[str]
) -> tuple[str | None, list[str], list[str]]:
    """Fields after the Chinese meaning: one written as /…/ or […] is the
    pronunciation (spec 017), one like "adj." or "n. v." the part of speech
    (spec 019); the rest are extra accepted answers. Returns (ipa, pos,
    alternates)."""
    extras = [f for f in extras if f]
    pronunciations = [f for f in extras if _is_pronunciation(f)]
    pos_fields = [f for f in extras if not _is_pronunciation(f) and is_pos_field(f)]
    alternates = [f for f in extras if f not in pronunciations and f not in pos_fields]
    ipa = None
    if pronunciations:
        ipa, problem = normalize_ipa(pronunciations[0])
        if problem:
            skipped.append(f'line {number}: "{pronunciations[0]}" is not a pronunciation')
        if len(pronunciations) > 1:
            skipped.append(f"line {number}: more than one pronunciation — kept the first")
    pos: list[str] = []
    if pos_fields:
        pos = normalize_pos(pos_fields[0])[0] or []
        if len(pos_fields) > 1:
            skipped.append(f"line {number}: more than one part of speech — kept the first")
    return ipa, pos, alternates


def _meaning_slot(fields: list[str]) -> tuple[str | None, list[str]]:
    """The Chinese meaning is the first field after the English word that
    is neither a pronunciation nor a part of speech; an empty one means
    there is none. Returns (chinese, the other fields)."""
    rest = list(fields[1:])
    for index, value in enumerate(rest):
        if value and (_is_pronunciation(value) or is_pos_field(value)):
            continue
        return (value or None), rest[:index] + rest[index + 1 :]
    return None, rest


def _simple_item(number: int, fields: list[str], skipped: list[str]) -> VocabularyItem:
    chinese, extras = _meaning_slot(fields)
    ipa, pos, alternates = _split_extras(number, extras, skipped)
    return VocabularyItem(fields[0], chinese, alternates, ipa=ipa, pos=pos)


def _simple_draft(number: int, fields: list[str], skipped: list[str]) -> DraftWord:
    # Spec 018: the Chinese meaning is optional.
    chinese, extras = _meaning_slot(fields)
    ipa, pos, alternates = _split_extras(number, extras, skipped)
    return DraftWord(fields[0], chinese, ipa, alternates, f"line {number}", pos=pos)


def _parse_simple(text: str, require_chinese: bool = True) -> ParsedUpload:
    parsed = ParsedUpload()
    first_row = True
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        fields = _split_line(line)
        if first_row:
            first_row = False
            if fields and fields[0].lower() in HEADER_WORDS:
                continue
        if not fields or not fields[0]:
            parsed.skipped.append(f"line {number}: no English word")
        elif not require_chinese:
            parsed.items.append(_simple_draft(number, fields, parsed.skipped))
        elif _meaning_slot(fields)[0] is None:
            parsed.skipped.append(f"line {number}: no Chinese meaning")
        else:
            parsed.items.append(_simple_item(number, fields, parsed.skipped))
    return parsed


def _markdown_draft(number: int, block: dict, skipped: list[str]) -> DraftWord | None:
    english = block.get("english")
    if not isinstance(english, str) or not english.strip():
        skipped.append(f"block {number}: missing 'english'")
        return None
    alternates = block.get("alternates") or []
    if not isinstance(alternates, list) or not all(isinstance(a, str) for a in alternates):
        skipped.append(f"block {number}: alternates must be a list of words")
        return None
    chinese = block.get("chinese")
    chinese = chinese.strip() if isinstance(chinese, str) and chinese.strip() else None
    ipa, problem = normalize_ipa(block.get("ipa"))
    if problem:
        skipped.append(f"block {number}: {problem}")
    pos, pos_problem = normalize_pos(block.get("pos"))
    if pos_problem:
        skipped.append(f"block {number}: {pos_problem}")
    # Any group is ignored: the list name becomes the group when saved.
    return DraftWord(
        english.strip(), chinese, ipa, list(alternates), f"block {number}", pos=pos or []
    )


# Markdown list markers: "- word", "* word", "+ word", "1. word", "1) word".
_LIST_MARKER = re.compile(r"^[ \t]*(?:[-*+]|\d+[.)])[ \t]+", re.MULTILINE)


def _parse_markdown(text: str, require_chinese: bool = True) -> ParsedUpload:
    if not require_chinese and not _BLOCK_RE.search(text):
        # Spec 018: a .md file of plain lines (perhaps a bulleted list) is
        # a simple word list; "#" headings are skipped like comments.
        return _parse_simple(_LIST_MARKER.sub("", text), require_chinese=False)
    parsed = ParsedUpload()
    # Parse block by block so each skipped one can be reported by number.
    for number, match in enumerate(_BLOCK_RE.finditer(text), start=1):
        blocks, warnings = parse_blocks(match.group(0))
        if not blocks:
            reason = warnings[0] if warnings else "could not be read"
            parsed.skipped.append(f"block {number}: {reason}")
            continue
        if not require_chinese:
            draft = _markdown_draft(number, blocks[0], parsed.skipped)
            if draft is not None:
                parsed.items.append(draft)
            continue
        try:
            item = VocabularyItem.from_block(blocks[0])
        except VocabularyItemError as exc:
            message = str(exc)
            if "missing" in message:
                missing = "english" if "english" not in blocks[0] else "chinese"
                message = f"missing '{missing}'"
            parsed.skipped.append(f"block {number}: {message}")
            continue
        # The list name becomes the group when the list is saved.
        item.group = None
        parsed.items.append(item)
        if item.ipa_problem:
            parsed.skipped.append(f"block {number}: {item.ipa_problem}")
        if item.pos_problem:
            parsed.skipped.append(f"block {number}: {item.pos_problem}")
    return parsed


def parse_upload(filename: str, data: bytes, require_chinese: bool = True) -> ParsedUpload:
    """Parse an uploaded word list. By default (spec 016) every word needs
    a Chinese meaning and items are VocabularyItems; with
    require_chinese=False (spec 018 imports) items are DraftWords and only
    the English word is required."""
    suffix = Path(filename).suffix.lower()
    if suffix in MARKDOWN_EXTENSIONS:
        parser = _parse_markdown
    elif suffix in SIMPLE_EXTENSIONS:
        parser = _parse_simple
    else:
        shown = suffix or Path(filename).name
        raise UploadFormatError(
            f'Unsupported file type "{shown}". Upload a .csv, .txt or .md file.'
        )

    parsed = parser(_decode(data), require_chinese=require_chinese)
    if len(parsed.items) > MAX_WORDS:
        raise UploadFormatError(
            f"That list has {len(parsed.items)} words; the limit is {MAX_WORDS:,}."
        )
    return parsed


def sanitize_list_name(stem: str) -> str:
    """Keep letters, digits, spaces, "-" and "_" (any script); collapse
    whitespace; no leading dots; at most 64 characters. May return ""."""
    kept = "".join(ch for ch in stem if ch.isalnum() or ch in " -_")
    name = " ".join(kept.split()).lstrip(". ")
    return name[:MAX_NAME_LENGTH].strip()


class _FlowList(list):
    """A list written on one line, as `pos: [n., v.]` (spec 019)."""


class _Dumper(yaml.SafeDumper):
    pass


_Dumper.add_representer(
    _FlowList,
    lambda dumper, data: dumper.represent_sequence(
        "tag:yaml.org,2002:seq", data, flow_style=True
    ),
)


def _dump_block(block: dict) -> str:
    if block.get("pos"):
        block = {**block, "pos": _FlowList(block["pos"])}
    yaml_text = yaml.dump(
        block, Dumper=_Dumper, allow_unicode=True, sort_keys=False, default_flow_style=False
    )
    return f"---\n{yaml_text}---\n"


def _to_markdown(name: str, items: list[VocabularyItem]) -> str:
    chunks = []
    for item in items:
        block = {"english": item.english}
        if item.ipa:
            block["ipa"] = item.ipa
        if item.pos:
            block["pos"] = list(item.pos)
        block.update(
            {"alternates": list(item.alternates), "chinese": item.chinese, "group": name}
        )
        chunks.append(_dump_block(block))
    return "\n".join(chunks)


def _updated_block(block: dict, fields: dict) -> dict:
    """*block* with ipa and pos (each dropped when empty), alternates and
    chinese taken from *fields*. Other keys and the key order are kept;
    ipa and pos go right after english, where _to_markdown writes them."""
    updated: dict = {}
    for key, value in block.items():
        if key in ("ipa", "pos"):
            continue
        updated[key] = value
        if key == "english":
            if fields.get("ipa"):
                updated["ipa"] = fields["ipa"]
            if fields.get("pos"):
                updated["pos"] = list(fields["pos"])
    updated["alternates"] = list(fields.get("alternates") or [])
    updated["chinese"] = fields["chinese"]
    return updated


def _replaced_values(block_text: str, values) -> str:
    """*block_text* (from its opening to its closing ---) with the ipa,
    chinese and pos keys set from *values* (spec 023): each replaced in
    place on one line, a missing ipa or pos added right after english,
    and every other line kept byte for byte."""
    lines = block_text.split("\n")
    opening, body, closing = lines[0], lines[1:-1], lines[-1]
    # Top-level keys start at column 0; indented or "- " lines continue one.
    segments: list[tuple[str | None, list[str]]] = []
    for line in body:
        starts_key = line[:1] not in (" ", "\t", "-", "#", "") and ":" in line
        key = line.split(":", 1)[0] if starts_key else None
        if key is not None or not segments:
            segments.append((key, [line]))
        else:
            segments[-1][1].append(line)

    def dumped(key: str, value) -> list[str]:
        if key == "pos":
            return [f"pos: [{', '.join(value)}]"]
        text = yaml.safe_dump(
            {key: value}, allow_unicode=True, default_flow_style=False, width=10_000
        )
        return text.rstrip("\n").split("\n")

    wanted = {"ipa": values.ipa, "chinese": values.chinese, "pos": list(values.pos)}
    present = {key for key, _ in segments}
    out: list[str] = []
    for key, seg_lines in segments:
        if key in wanted:
            if wanted[key]:
                out.extend(dumped(key, wanted[key]))
            continue
        out.extend(seg_lines)
        if key == "english":
            for extra in ("ipa", "pos"):
                if extra not in present and wanted[extra]:
                    out.extend(dumped(extra, wanted[extra]))
    if "chinese" not in present:
        out.extend(dumped("chinese", wanted["chinese"]))
    return "\n".join([opening, *out, closing])


def _write_text(path: Path, text: str) -> None:
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, suffix=".tmp", delete=False, newline=""
    ) as tmp:
        tmp.write(text)
    try:
        os.replace(tmp.name, path)
    except BaseException:
        Path(tmp.name).unlink(missing_ok=True)
        raise


def _write_all_or_nothing(writes: dict[Path, str]) -> None:
    """Write every file, or (on any error) leave every file as it was:
    stage temp files, back up the originals, then swap each into place."""
    temps: dict[Path, Path] = {}
    backups: dict[Path, Path] = {}
    replaced: list[Path] = []
    try:
        for path, text in writes.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", dir=path.parent, suffix=".tmp", delete=False
            ) as tmp:
                tmp.write(text)
            temps[path] = Path(tmp.name)
        for path in writes:
            if path.exists():
                backup = path.with_name(path.name + ".bak")
                shutil.copy2(path, backup)
                backups[path] = backup
        for path, temp in temps.items():
            os.replace(temp, path)
            replaced.append(path)
    except BaseException:
        for path in replaced:
            if path in backups:
                shutil.copy2(backups[path], path)
            else:
                path.unlink(missing_ok=True)
        for leftover in [*temps.values(), *backups.values()]:
            leftover.unlink(missing_ok=True)
        raise
    for backup in backups.values():
        backup.unlink(missing_ok=True)


class WordListStore:
    def __init__(self, root: Path):
        self.root = root
        self._locks: dict[str, threading.Lock] = {}
        self._locks_guard = threading.Lock()

    def _lock(self, account: Account) -> threading.Lock:
        with self._locks_guard:
            return self._locks.setdefault(account.username, threading.Lock())

    def folder(self, account: Account) -> Path:
        return self.root / account.username

    def _lists(self, account: Account) -> list[Path]:
        folder = self.folder(account)
        if not folder.is_dir():
            return []
        return sorted(folder.glob("*.md"))

    def _find(self, account: Account, name: str) -> Path | None:
        wanted = name.lower()
        for path in self._lists(account):
            if path.stem.lower() == wanted:
                return path
        return None

    def save(
        self, account: Account, name: str, items: list[VocabularyItem], replace: bool = False
    ) -> SaveResult:
        with self._lock(account):
            first_list = not self._lists(account)
            if not name:
                name = DEFAULT_LIST_NAME
                number = 2
                while self._find(account, name):
                    name = f"{DEFAULT_LIST_NAME} {number}"
                    number += 1

            existing = self._find(account, name)
            if existing is not None and not replace:
                raise ListExistsError(existing.stem)
            if existing is not None:
                name = existing.stem
            target = existing or self.folder(account) / f"{name}.md"

            target.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", dir=target.parent, suffix=".tmp", delete=False
            ) as tmp:
                tmp.write(_to_markdown(name, items))
            os.replace(tmp.name, target)
            return SaveResult(name=name, replaced=existing is not None, first_list=first_list)

    def lock(self, account: Account) -> threading.Lock:
        return self._lock(account)

    def apply_import(
        self,
        account: Account,
        name: str,
        new_items: list[VocabularyItem],
        updates: dict[str, list[tuple[str, dict]]] | None = None,
        replace: bool = False,
    ) -> SaveResult:
        """Save a confirmed import (spec 018, research R8): the new list,
        plus in-place updates to existing entries of other lists, written
        all-or-nothing — on any failure every file is left as it was."""
        with self._lock(account):
            first_list = not self._lists(account)
            existing = self._find(account, name) if new_items else None
            if existing is not None and not replace:
                raise ListExistsError(existing.stem)
            if existing is not None:
                name = existing.stem

            writes: dict[Path, str] = {}
            if new_items:
                target = existing or self.folder(account) / f"{name}.md"
                writes[target] = _to_markdown(name, new_items)
            writes.update(self._render_updates(account, updates or {}))
            _write_all_or_nothing(writes)
            return SaveResult(name=name, replaced=existing is not None, first_list=first_list)

    def _render_updates(
        self, account: Account, updates: dict[str, list[tuple[str, dict]]]
    ) -> dict[Path, str]:
        """Re-render each list named in *updates* with only the matching
        entries' ipa/chinese/alternates changed; every other block keeps
        all its keys and values. Lists not named are never touched."""
        rendered: dict[Path, str] = {}
        for list_name, changes in updates.items():
            path = self._find(account, list_name)
            if path is None:
                raise KeyError(list_name)
            wanted = {english.strip().casefold(): fields for english, fields in changes}
            blocks, _warnings = parse_blocks(path.read_text(encoding="utf-8"))
            chunks = []
            for block in blocks:
                english = block.get("english")
                fields = wanted.get(english.strip().casefold()) if isinstance(english, str) else None
                if fields is not None:
                    block = _updated_block(block, fields)
                chunks.append(_dump_block(block))
            rendered[path] = "\n".join(chunks)
        return rendered

    # --- removing single words (spec 020) ---------------------------------

    def _own_path(self, account: Account, path: Path) -> Path:
        resolved = Path(path).resolve()
        if not resolved.is_relative_to(self.folder(account).resolve()):
            raise ValueError(f"{path} is not one of {account.username}'s lists")
        return resolved

    def remove_word(self, account: Account, path: Path, english: str, chinese: str) -> RemovedEntry:
        """Cut the first block matching *english* and *chinese* out of one of
        the account's list files; every other byte stays the same."""
        with self._lock(account):
            target = self._own_path(account, path)
            text = target.read_text(encoding="utf-8")
            match = self._find_block(text, english, chinese)
            if match is not None:
                start, end = match.start(), match.end()
                if text[end : end + 1] == "\n":
                    end += 1  # the block's own line end
                if text[end : end + 1] == "\n":
                    end += 1  # one separator line after it
                elif start > 0 and text[start - 1 : start] == "\n" and end >= len(text):
                    start -= 1  # last block: take the separator before it
                after = text[:start] + text[end:]
                _write_text(target, after)
                return RemovedEntry(target, start, text[start:end], after)
            raise KeyError(english)

    def set_example(
        self, account: Account, path: Path, english: str, chinese: str, sentence: str, translation: str
    ) -> None:
        """Save an example in the word's own block (spec 021): the block's
        `example:`/`example_zh:` lines are replaced, or added before its
        closing `---`; every other byte stays the same."""
        with self._lock(account):
            target = self._own_path(account, path)
            text = target.read_text(encoding="utf-8")
            match = self._find_block(text, english, chinese)
            if match is None:
                raise KeyError(english)
            start = match.start()
            end = start + len(match.group(0).rstrip())  # up to the closing ---
            lines = text[start:end].split("\n")
            # Examples are always written on one line (width below).
            kept = [line for line in lines[:-1] if not line.startswith(("example:", "example_zh:"))]
            dumped = yaml.safe_dump(
                {"example": sentence, "example_zh": translation},
                allow_unicode=True, sort_keys=False, default_flow_style=False, width=10_000,
            ).rstrip("\n")
            new_body = "\n".join([*kept, dumped, lines[-1]])
            _write_text(target, text[:start] + new_body + text[end:])

    def word_values(self, account: Account, path: Path, english: str) -> list:
        """The checked values (spec 023) of every block for *english* in one
        of the account's lists, in file order."""
        target = self._own_path(account, path)
        try:
            text = target.read_text(encoding="utf-8")
        except OSError:
            return []
        blocks, _ = parse_blocks(text)
        return [
            WordValues.normal(b.get("ipa"), str(b.get("chinese", "")), b.get("pos") or [])
            for b in blocks
            if str(b.get("english", "")).strip() == english.strip()
        ]

    def set_values(self, account: Account, path: Path, english: str, old, new) -> bool:
        """Replace a word's ipa, chinese and pos (spec 023) with *new*, but
        only in a block for *english* whose values still equal *old*
        (WordValues); False, writing nothing, when there is none. Every
        other line of the block and the file stays the same."""
        with self._lock(account):
            target = self._own_path(account, path)
            text = target.read_text(encoding="utf-8")
            for match in _BLOCK_RE.finditer(text):
                blocks, _ = parse_blocks(match.group(0))
                if not blocks:
                    continue
                block = blocks[0]
                if str(block.get("english", "")).strip() != english.strip():
                    continue
                current = WordValues.normal(
                    block.get("ipa"), str(block.get("chinese", "")), block.get("pos") or []
                )
                if current != old:
                    continue
                start = match.start()
                end = start + len(match.group(0).rstrip())
                body = _replaced_values(text[start:end], new)
                _write_text(target, text[:start] + body + text[end:])
                return True
            return False

    def _find_block(self, text: str, english: str, chinese: str):
        for match in _BLOCK_RE.finditer(text):
            blocks, _ = parse_blocks(match.group(0))
            if not blocks:
                continue
            block = blocks[0]
            if str(block.get("english", "")).strip() == english.strip() and str(
                block.get("chinese", "")
            ).strip() == chinese.strip():
                return match
        return None

    def restore_word(self, account: Account, removed: RemovedEntry) -> None:
        """Put a cut entry back: exactly where it was if the file is as the
        cut left it, otherwise before the first block at or after that
        place, so nothing is lost."""
        with self._lock(account):
            target = self._own_path(account, removed.path)
            text = target.read_text(encoding="utf-8") if target.exists() else ""
            if text == removed.file_after:
                restored = text[: removed.offset] + removed.text + text[removed.offset :]
            else:
                starts = [m.start() for m in _BLOCK_RE.finditer(text) if m.start() >= removed.offset]
                entry = removed.text.strip("\n") + "\n"
                if starts:
                    restored = text[: starts[0]] + entry + "\n" + text[starts[0] :]
                else:
                    restored = (text.rstrip("\n") + "\n\n" if text.strip() else "") + entry
            _write_text(target, restored)

    def _hidden_path(self, account: Account) -> Path:
        return self.folder(account) / ".hidden-shared.json"

    def _read_hidden(self, account: Account) -> list[dict]:
        try:
            data = json.loads(self._hidden_path(account).read_text(encoding="utf-8"))
            return [h for h in data.get("hidden", []) if isinstance(h, dict)]
        except (OSError, ValueError, AttributeError):
            return []

    def _write_hidden(self, account: Account, hidden: list[dict]) -> None:
        path = self._hidden_path(account)
        path.parent.mkdir(parents=True, exist_ok=True)
        _write_text(path, json.dumps({"version": 1, "hidden": hidden}, ensure_ascii=False, indent=2))

    def hidden_shared(self, account: Account) -> set[tuple]:
        """Shared words this account removed: (group, english, chinese)."""
        return {(h.get("group"), h.get("english"), h.get("chinese")) for h in self._read_hidden(account)}

    def hide_shared(self, account: Account, group, english: str, chinese: str) -> None:
        with self._lock(account):
            hidden = self._read_hidden(account)
            entry = {"group": group, "english": english, "chinese": chinese}
            if entry not in hidden:
                hidden.append(entry)
            self._write_hidden(account, hidden)

    def unhide_shared(self, account: Account, group, english: str, chinese: str) -> None:
        with self._lock(account):
            entry = {"group": group, "english": english, "chinese": chinese}
            self._write_hidden(account, [h for h in self._read_hidden(account) if h != entry])

    def list(self, account: Account) -> list[dict]:
        lists = []
        for path in self._lists(account):
            blocks, _ = parse_blocks(path.read_text(encoding="utf-8"))
            uploaded = datetime.fromtimestamp(path.stat().st_mtime, UTC)
            lists.append(
                {
                    "name": path.stem,
                    "word_count": len(blocks),
                    "uploaded_at": uploaded.isoformat(timespec="seconds"),
                }
            )
        return sorted(lists, key=lambda entry: entry["name"].lower())

    def delete(self, account: Account, name: str) -> str:
        with self._lock(account):
            path = self._find(account, sanitize_list_name(name))
            if path is None:
                raise KeyError(name)
            path.unlink()
            return path.stem

    def effective_dir(self, account: Account, shared: Path) -> Path:
        return self.folder(account) if self._lists(account) else shared

    def word_source(self, account: Account) -> str:
        return "own" if self._lists(account) else "shared"
