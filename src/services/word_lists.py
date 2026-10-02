"""Per-account uploaded word lists (spec 016, contracts/upload-formats.md).

parse_upload() turns an uploaded vocabulary Markdown file or simple
"English, Chinese" list into VocabularyItems; WordListStore saves each list
as vocabulary Markdown under <root>/<username>/<name>.md, so an account's
folder is just another vocabulary directory for load_vocabulary()."""

import csv
import os
import tempfile
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import yaml

from src.lib.markdown_blocks import _BLOCK_RE, parse_blocks
from src.models.account import Account
from src.models.vocabulary_item import VocabularyItem, VocabularyItemError

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
class ParsedUpload:
    items: list[VocabularyItem] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


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


def _parse_simple(text: str) -> ParsedUpload:
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
        elif len(fields) < 2 or not fields[1]:
            parsed.skipped.append(f"line {number}: no Chinese meaning")
        else:
            alternates = [f for f in fields[2:] if f]
            parsed.items.append(VocabularyItem(fields[0], fields[1], alternates))
    return parsed


def _parse_markdown(text: str) -> ParsedUpload:
    parsed = ParsedUpload()
    # Parse block by block so each skipped one can be reported by number.
    for number, match in enumerate(_BLOCK_RE.finditer(text), start=1):
        blocks, warnings = parse_blocks(match.group(0))
        if not blocks:
            reason = warnings[0] if warnings else "could not be read"
            parsed.skipped.append(f"block {number}: {reason}")
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
    return parsed


def parse_upload(filename: str, data: bytes) -> ParsedUpload:
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

    parsed = parser(_decode(data))
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


def _to_markdown(name: str, items: list[VocabularyItem]) -> str:
    chunks = []
    for item in items:
        block = {
            "english": item.english,
            "alternates": list(item.alternates),
            "chinese": item.chinese,
            "group": name,
        }
        yaml_text = yaml.safe_dump(
            block, allow_unicode=True, sort_keys=False, default_flow_style=False
        )
        chunks.append(f"---\n{yaml_text}---\n")
    return "\n".join(chunks)


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
