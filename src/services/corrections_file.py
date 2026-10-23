"""The hidden `.corrections.json` beside the word files (spec 023,
contracts/corrections-file.md).

One per word folder: the shared folder's holds the overlay of corrected
values that the loader applies for everyone; each folder's holds the
fingerprints of checked words and the correction records. Readers
tolerate a missing or damaged file part by part and never fail; writers
rewrite the whole file atomically under a per-file lock. Nothing here
identifies a learner."""

import hashlib
import json
import os
import secrets
import tempfile
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TypeVar

from src.lib.ipa import normalize_ipa
from src.lib.pos import normalize_pos

FILE_NAME = ".corrections.json"
VERSION = 1
MAX_CHECKED = 20_000
MAX_RECORDS = 500
FIELDS = ("ipa", "chinese", "pos")

T = TypeVar("T")


@dataclass(frozen=True)
class WordValues:
    """The three checked fields of a word, normalised: IPA without
    slashes, meaning trimmed, parts of speech as labels."""

    ipa: str | None
    chinese: str
    pos: tuple[str, ...]

    @classmethod
    def normal(cls, ipa, chinese, pos) -> "WordValues":
        bare, _ = normalize_ipa(ipa)
        labels, _ = normalize_pos(list(pos) if pos else None)
        return cls(bare, (chinese or "").strip(), tuple(labels or ()))

    def get(self, name: str):
        value = getattr(self, name)
        return list(value) if name == "pos" else value

    def to_json(self) -> dict:
        return {"ipa": self.ipa, "chinese": self.chinese, "pos": list(self.pos)}

    @classmethod
    def from_json(cls, data) -> "WordValues":
        if not isinstance(data, dict):
            raise TypeError("not an object")
        ipa, chinese, pos = data.get("ipa"), data.get("chinese"), data.get("pos")
        if (
            (ipa is not None and not isinstance(ipa, str))
            or not isinstance(chinese, str)
            or not chinese.strip()
            or not isinstance(pos, list)
            or not all(isinstance(p, str) for p in pos)
        ):
            raise ValueError("bad values")
        return cls.normal(ipa, chinese, pos)


def fingerprint(file_name: str, group: str | None, english: str, values: WordValues) -> str:
    text = "|".join(
        [file_name, group or "", english, values.ipa or "", values.chinese, " ".join(values.pos)]
    )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def overlay_key(file_name: str, group: str | None, english: str, origin_chinese: str) -> str:
    return f"{file_name}|{group or ''}|{english}|{origin_chinese}"


def new_id() -> str:
    return secrets.token_hex(6)


def _is_value(value) -> bool:
    return (
        value is None
        or isinstance(value, str)
        or (isinstance(value, list) and all(isinstance(v, str) for v in value))
    )


@dataclass(frozen=True)
class CorrectionRecord:
    """One saved change to one field of one word (data-model.md)."""

    id: str
    batch: str
    file: str
    group: str | None
    english: str
    origin_chinese: str
    field: str
    old: str | list[str] | None
    new: str | list[str] | None
    at: str
    undone_at: str | None = None

    def to_json(self) -> dict:
        return {
            "id": self.id,
            "batch": self.batch,
            "file": self.file,
            "group": self.group,
            "english": self.english,
            "origin_chinese": self.origin_chinese,
            "field": self.field,
            "old": self.old,
            "new": self.new,
            "at": self.at,
            "undone_at": self.undone_at,
        }

    @classmethod
    def from_json(cls, data) -> "CorrectionRecord":
        if not isinstance(data, dict):
            raise TypeError("not an object")
        strings = ("id", "batch", "file", "english", "origin_chinese", "at")
        if not all(isinstance(data.get(k), str) and data.get(k) for k in strings):
            raise ValueError("missing field")
        if data.get("field") not in FIELDS:
            raise ValueError("bad field")
        if data.get("group") is not None and not isinstance(data.get("group"), str):
            raise ValueError("bad group")
        if not _is_value(data.get("old")) or not _is_value(data.get("new")):
            raise ValueError("bad value")
        if data.get("undone_at") is not None and not isinstance(data.get("undone_at"), str):
            raise ValueError("bad undone_at")
        return cls(**{k: data.get(k) for k in cls.__dataclass_fields__})


@dataclass
class CorrectionsData:
    overlay: dict[str, WordValues] = field(default_factory=dict)
    checked: list[str] = field(default_factory=list)
    records: list[CorrectionRecord] = field(default_factory=list)

    def is_checked(self, fp: str) -> bool:
        return fp in self.checked

    def mark_checked(self, fp: str) -> None:
        if fp not in self.checked:
            self.checked.append(fp)
            del self.checked[:-MAX_CHECKED]

    def add_records(self, records: list[CorrectionRecord]) -> None:
        """Add one check's records (in field order) before the older ones."""
        self.records[:0] = records
        del self.records[MAX_RECORDS:]

    def replace_record(self, record: CorrectionRecord) -> None:
        self.records = [record if r.id == record.id else r for r in self.records]


def read(folder: Path) -> CorrectionsData:
    """The folder's corrections; anything unreadable counts as empty."""
    data = CorrectionsData()
    try:
        raw = json.loads((Path(folder) / FILE_NAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return data
    if not isinstance(raw, dict) or raw.get("version") != VERSION:
        return data

    overlay = raw.get("overlay")
    if isinstance(overlay, dict):
        for key, values in overlay.items():
            try:
                data.overlay[key] = WordValues.from_json(values)
            except (TypeError, ValueError):
                continue
    checked = raw.get("checked")
    if isinstance(checked, list):
        data.checked = [fp for fp in checked if isinstance(fp, str)][-MAX_CHECKED:]
    records = raw.get("records")
    if isinstance(records, list):
        for entry in records:
            try:
                data.records.append(CorrectionRecord.from_json(entry))
            except (TypeError, ValueError):
                continue
        del data.records[MAX_RECORDS:]
    return data


def write(folder: Path, data: CorrectionsData) -> None:
    """Rewrite the whole file: a temp file in the same folder, then
    os.replace, so a failed write leaves the old file intact."""
    folder = Path(folder)
    text = json.dumps(
        {
            "version": VERSION,
            "overlay": {key: values.to_json() for key, values in data.overlay.items()},
            "checked": data.checked,
            "records": [r.to_json() for r in data.records],
        },
        ensure_ascii=False,
        indent=2,
    )
    folder.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=folder, prefix=".corrections-", suffix=".tmp", delete=False
    ) as tmp:
        tmp.write(text)
    try:
        os.replace(tmp.name, folder / FILE_NAME)
    except OSError:
        Path(tmp.name).unlink(missing_ok=True)
        raise


_locks: dict[Path, threading.Lock] = {}
_locks_guard = threading.Lock()


def lock(folder: Path) -> threading.Lock:
    path = (Path(folder) / FILE_NAME).resolve()
    with _locks_guard:
        return _locks.setdefault(path, threading.Lock())


def update(folder: Path, fn: Callable[[CorrectionsData], T]) -> T:
    """Read, apply *fn*, write, under the file's lock; returns fn's result."""
    with lock(folder):
        data = read(folder)
        result = fn(data)
        write(folder, data)
        return result
