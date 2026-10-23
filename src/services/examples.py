"""Example sentences for vocabulary, made on first practice and then kept
(spec 021, research R5/R6).

ExampleService generates an example with the local model in the
background as soon as a word comes up, checks it (validate_example), and
saves it: in the word's own block for a learner's own list, otherwise in
a hidden `.examples.json` beside the word's file, so shared vocabulary
files are never edited. A bound view (`bind(account)`) is what a
practice session uses."""

import json
import os
import tempfile
import threading
from datetime import UTC, datetime
from pathlib import Path

from src.models.account import Account
from src.models.vocabulary_item import VocabularyItem
from src.services.example_client import request_example, validate_example
from src.services.word_lists import WordListStore

EXAMPLES_FILENAME = ".examples.json"
ATTEMPTS = 2  # an invalid example is retried once


class ExampleUnavailable(Exception):
    """No valid example could be made right now."""


def _same_sentence(a: str, b: str) -> bool:
    return " ".join(a.casefold().split()) == " ".join(b.casefold().split())


def _json_key(item: VocabularyItem) -> str:
    return f"{item.group or ''}|{item.english}|{item.origin_chinese}"


class ExampleService:
    def __init__(
        self,
        word_lists: WordListStore | None,
        base_url: str,
        model: str,
        generate=request_example,
    ):
        self.word_lists = word_lists
        self.base_url = base_url
        self.model = model
        self.generate = generate
        self._lock = threading.Lock()
        self._known: dict[str, dict] = {}
        self._status: dict[str, str] = {}
        self._threads: dict[str, threading.Thread] = {}
        self._file_locks: dict[Path, threading.Lock] = {}

    def bind(self, account: Account | None) -> "BoundExamples":
        return BoundExamples(self, account)

    # --- lookup -----------------------------------------------------------

    def _key(self, item: VocabularyItem) -> str:
        return f"{item.source}|{_json_key(item)}"

    def _own(self, account: Account | None, item: VocabularyItem) -> bool:
        if self.word_lists is None or account is None or item.source is None:
            return False
        folder = self.word_lists.folder(account).resolve()
        return Path(item.source).resolve().is_relative_to(folder)

    def get(self, account: Account | None, item: VocabularyItem) -> dict | None:
        known = self._known.get(self._key(item))
        if known:
            return known
        if item.example and item.example_zh:
            return {"sentence": item.example, "translation": item.example_zh}
        if item.source is not None and not self._own(account, item):
            saved = self._read_json(Path(item.source).parent).get(_json_key(item))
            if saved:
                return {"sentence": saved["sentence"], "translation": saved["translation"]}
        return None

    def status(self, account: Account | None, item: VocabularyItem) -> str:
        if self.get(account, item):
            return "ready"
        key = self._key(item)
        thread = self._threads.get(key)
        if thread is not None and thread.is_alive():
            return "pending"
        return self._status.get(key, "unavailable")

    # --- making examples ----------------------------------------------------

    def prepare(self, account: Account | None, item: VocabularyItem) -> None:
        """Start making the word's example in the background, unless it
        exists or is already being made."""
        if self.get(account, item):
            return
        key = self._key(item)
        with self._lock:
            thread = self._threads.get(key)
            if thread is not None and thread.is_alive():
                return
            self._status[key] = "pending"
            thread = threading.Thread(target=self._make, args=(account, item), daemon=True)
            self._threads[key] = thread
            thread.start()

    def wait(self, account: Account | None, item: VocabularyItem, timeout: float | None = None) -> None:
        thread = self._threads.get(self._key(item))
        if thread is not None:
            thread.join(timeout)

    def wait_all(self, timeout: float | None = None) -> None:
        """Join every example still being made (tests and shutdown)."""
        for thread in list(self._threads.values()):
            thread.join(timeout)

    def renew(self, account: Account | None, item: VocabularyItem) -> dict:
        """Make a different example now and keep it instead of the old one."""
        old = self.get(account, item)
        example = self._generate_valid(item, avoid=old["sentence"] if old else None)
        if example is None:
            raise ExampleUnavailable(item.english)
        self._save(account, item, example)
        return example

    def _make(self, account: Account | None, item: VocabularyItem) -> None:
        example = self._generate_valid(item)
        if example is None:
            self._status[self._key(item)] = "unavailable"
            return
        self._save(account, item, example)

    def _generate_valid(self, item: VocabularyItem, avoid: str | None = None) -> dict | None:
        """A checked example, or None. With *avoid* (renewing), a reply
        that repeats that sentence counts as invalid."""
        args = (item.english, item.chinese, list(item.pos), self.base_url, self.model)
        for _ in range(ATTEMPTS):
            reply = self.generate(*args, avoid=avoid) if avoid else self.generate(*args)
            if reply.outcome == "unavailable":
                return None
            if reply.outcome == "ok":
                ok, _reason = validate_example(item.english, reply.sentence, reply.translation)
                if ok and avoid and _same_sentence(reply.sentence, avoid):
                    ok = False
                if ok:
                    return {"sentence": reply.sentence, "translation": reply.translation}
        return None

    # --- saving -----------------------------------------------------------

    def _save(self, account: Account | None, item: VocabularyItem, example: dict) -> None:
        """Write the example, then mark it ready (so a reader that sees
        "ready" also finds it on disk)."""
        if self._own(account, item):
            try:
                self.word_lists.set_example(
                    account, item.source, item.english, item.origin_chinese,
                    example["sentence"], example["translation"],
                )  # fmt: skip
            except (KeyError, OSError):
                pass  # the word left its list meanwhile; keep it for this session
        elif item.source is not None:
            self._write_json(Path(item.source).parent, _json_key(item), example)
        key = self._key(item)
        self._known[key] = example
        self._status[key] = "ready"

    def _file_lock(self, path: Path) -> threading.Lock:
        with self._lock:
            return self._file_locks.setdefault(path, threading.Lock())

    def _read_json(self, folder: Path) -> dict:
        try:
            data = json.loads((folder / EXAMPLES_FILENAME).read_text(encoding="utf-8"))
            examples = data.get("examples", {})
            return examples if isinstance(examples, dict) else {}
        except (OSError, ValueError, AttributeError):
            return {}

    def _write_json(self, folder: Path, key: str, example: dict) -> None:
        path = folder / EXAMPLES_FILENAME
        with self._file_lock(path):
            examples = self._read_json(folder)
            examples[key] = {**example, "created": datetime.now(UTC).isoformat(timespec="seconds")}
            text = json.dumps({"version": 1, "examples": examples}, ensure_ascii=False, indent=2)
            try:
                with tempfile.NamedTemporaryFile(
                    "w", encoding="utf-8", dir=folder, suffix=".tmp", delete=False
                ) as tmp:
                    tmp.write(text)
                os.replace(tmp.name, path)
            except OSError:
                pass  # a read-only folder: the example still shows this session


class BoundExamples:
    """ExampleService for one account (or none), as a session uses it."""

    def __init__(self, service: ExampleService, account: Account | None):
        self.service = service
        self.account = account

    def get(self, item: VocabularyItem) -> dict | None:
        return self.service.get(self.account, item)

    def status(self, item: VocabularyItem) -> str:
        return self.service.status(self.account, item)

    def prepare(self, item: VocabularyItem) -> None:
        self.service.prepare(self.account, item)

    def wait(self, item: VocabularyItem, timeout: float | None = None) -> None:
        self.service.wait(self.account, item, timeout)

    def renew(self, item: VocabularyItem) -> dict:
        return self.service.renew(self.account, item)

    def get_or_make(self, item: VocabularyItem, timeout: float) -> dict | None:
        """The word's example, making it now if needed and waiting at most
        *timeout* seconds (the command-line tutor)."""
        example = self.get(item)
        if example is None:
            self.prepare(item)
            self.wait(item, timeout)
            example = self.get(item)
        return example
