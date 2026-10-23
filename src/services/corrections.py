"""Automatic word corrections (spec 023).

The first time a word comes up in practice, CorrectionService checks its
IPA, meaning and parts of speech with Qwen in the background
(word_check.check_word) and saves a fully valid answer that differs: into
the word's block for a learner's own list, or into the shared folder's
overlay for the shared sets, which applies to every learner and leaves the
shared files untouched (FR-009). Every changed field is recorded
with its old value in the folder's `.corrections.json`, together with the
fingerprint of the values the word now has, so a word is sent once and
again only after it is edited. Practice never waits for a check.

Only the English word and its current values leave the machine; logs hold
the English word and the outcome, never the values, prompt or reply.
A bound view (`bind(account)`) is what a practice session uses."""

import logging
import math
import threading
import time
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from functools import partial
from pathlib import Path

from src.lib.ipa import check_american_ipa, check_british_ipa, normalize_ipa
from src.lib.markdown_blocks import parse_blocks
from src.models.account import Account
from src.models.vocabulary_item import VocabularyItem
from src.services import corrections_file as cf
from src.services import word_check
from src.services.corrections_file import FIELDS, CorrectionRecord, WordValues
from src.services.qwen_client import QwenConfig, QwenError
from src.services.word_lists import WordListStore

log = logging.getLogger(__name__)

MAX_PARALLEL = 2
PAUSE_SECONDS = 5 * 60
LIST_LIMIT = 200
_REMEMBERED = 500  # corrected items kept for the reveal note
# R8: the key won't fix itself; a busy or unreachable service may.
_PAUSE_UNTIL_RESTART = {"auth"}
_PAUSE_A_WHILE = {"timeout", "unavailable", "rate_limited"}


class CorrectionNotFound(KeyError):
    """No correction with that id that this learner can see."""


class AlreadyUndone(Exception):
    """The correction was undone before."""


class WordChanged(Exception):
    """The word was edited or removed since it was corrected."""


def _with(values: WordValues, changes: dict) -> WordValues:
    """*values* with some fields replaced (a pos list becomes a tuple)."""
    fixed = {
        name: tuple(v) if name == "pos" and v is not None else v for name, v in changes.items()
    }
    if "pos" in fixed and fixed["pos"] is None:
        fixed["pos"] = ()
    return replace(values, **fixed)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _iso(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def values_of(item: VocabularyItem) -> WordValues:
    return WordValues.normal(item.ipa, item.chinese, item.pos)


def _file_values(path: Path, english: str, chinese: str) -> WordValues | None:
    """A shared word's values as written in its file (no overlay)."""
    try:
        blocks, _ = parse_blocks(path.read_text(encoding="utf-8"))
    except OSError:
        return None
    for block in blocks:
        if (
            str(block.get("english", "")).strip() == english.strip()
            and str(block.get("chinese", "")).strip() == chinese.strip()
        ):
            return WordValues.normal(
                block.get("ipa"), str(block["chinese"]), block.get("pos") or []
            )
    return None


class CorrectionService:
    def __init__(
        self,
        word_lists: WordListStore | None,
        config: QwenConfig | None,
        shared_dir: Path | None = None,
        check=None,
        clock=time.monotonic,
        now=_utc_now,
    ):
        """*check* (english, ipa, chinese, pos, dialect) -> WordCheck
        defaults to word_check.check_word with *config*. Without either,
        the service only lists and undoes earlier corrections."""
        self.word_lists = word_lists
        self.shared_dir = Path(shared_dir) if shared_dir is not None else None
        self.enabled = check is not None or config is not None
        self.check = check or partial(word_check.check_word, config)
        self.clock = clock
        self.now = now
        self._lock = threading.Lock()
        self._slots = threading.Semaphore(MAX_PARALLEL)
        self._threads: dict[str, threading.Thread] = {}
        self._paused_until = 0.0
        self._pause_reason: str | None = None
        self._pause_wall: str | None = None
        # id(item) -> (item, fields): corrections saved this run, for the
        # "Updated" note at reveal. The item is kept so its id isn't reused.
        self._corrected: dict[int, tuple[VocabularyItem, list[str]]] = {}
        self._dialects: dict[tuple[Path, int], str] = {}

    def bind(self, account: Account | None) -> "BoundCorrections":
        return BoundCorrections(self, account)

    # --- where a word lives -------------------------------------------------

    def _own(self, account: Account | None, item: VocabularyItem) -> bool:
        if self.word_lists is None or account is None or item.source is None:
            return False
        folder = self.word_lists.folder(account).resolve()
        return Path(item.source).resolve().is_relative_to(folder)

    def _shared(self, item: VocabularyItem) -> bool:
        return (
            self.shared_dir is not None
            and item.source is not None
            and Path(item.source).resolve().parent == self.shared_dir.resolve()
        )

    def _scope(self, account: Account | None, item: VocabularyItem) -> str | None:
        """ "own", "shared", or None for a word this service doesn't correct."""
        if self._own(account, item):
            return "own"
        if self._shared(item):
            return "shared"
        return None

    def _dialect(self, item: VocabularyItem, scope: str) -> str:
        """British for the shared sets; for an own list, British when any of
        its words has an IPA only the British check accepts (a list copied
        from the shared sets), else American (research R3, per file)."""
        if scope == "shared":
            return "british"
        path = Path(item.source)
        try:
            stamp = (path, path.stat().st_mtime_ns)
        except OSError:
            return "american"
        cached = self._dialects.get(stamp)
        if cached is None:
            cached = "american"
            try:
                blocks, _ = parse_blocks(path.read_text(encoding="utf-8"))
            except OSError:
                blocks = []
            for block in blocks:
                ipa, _ = normalize_ipa(block.get("ipa"))
                if ipa and not check_british_ipa(ipa) and check_american_ipa(ipa):
                    cached = "british"
                    break
            self._dialects[stamp] = cached
        return cached

    # --- checking ---------------------------------------------------------------

    def paused(self) -> dict | None:
        with self._lock:
            if self.clock() < self._paused_until:
                return {"reason": self._pause_reason, "until": self._pause_wall}
            return None

    def prepare(self, account: Account | None, item: VocabularyItem) -> None:
        """Start checking *item* in the background unless it was checked,
        is being checked, or checks are paused. Returns at once."""
        if not self.enabled or item.source is None or self.paused() is not None:
            return
        scope = self._scope(account, item)
        if scope is None:
            return
        sent = values_of(item)
        folder = Path(item.source).parent
        fp = cf.fingerprint(Path(item.source).name, item.group, item.english, sent)
        if cf.read(folder).is_checked(fp):
            return
        key = f"{folder}|{fp}"
        with self._lock:
            running = self._threads.get(key)
            if running is not None and running.is_alive():
                return
            if len(self._threads) > 100:
                self._threads = {k: t for k, t in self._threads.items() if t.is_alive()}
            thread = threading.Thread(
                target=self._run, args=(account, item, scope, sent, fp), daemon=True
            )
            self._threads[key] = thread
        thread.start()

    def _run(self, account, item: VocabularyItem, scope: str, sent: WordValues, fp: str) -> None:
        with self._slots:
            if self.paused() is not None:
                return
            try:
                answer = self.check(
                    item.english, sent.ipa, sent.chinese, list(sent.pos), self._dialect(item, scope)
                )
            except QwenError as exc:
                self._failed(exc.code)
                log.info("Correction check for %r failed: %s", item.english, exc.code)
                return
            except Exception:  # noqa: BLE001 — never let a check break practice
                log.warning("Correction check for %r failed unexpectedly", item.english)
                return
        try:
            new = WordValues.normal(answer.ipa, answer.chinese, answer.pos)
            changed = [name for name in FIELDS if new.get(name) != sent.get(name)]
            saved = self._save(account, item, scope, sent, new, fp, changed)
        except (OSError, ValueError, KeyError):
            log.warning("Correction for %r could not be saved", item.english)
            return
        log.info(
            "Correction check for %r: %s",
            item.english,
            ", ".join(changed) + " corrected" if saved and changed else "unchanged",
        )

    def _failed(self, code: str) -> None:
        with self._lock:
            if code in _PAUSE_UNTIL_RESTART:
                self._paused_until = math.inf
                self._pause_wall = None
            elif code in _PAUSE_A_WHILE:
                self._paused_until = self.clock() + PAUSE_SECONDS
                self._pause_wall = _iso(self.now() + timedelta(seconds=PAUSE_SECONDS))
            else:
                return
            self._pause_reason = str(QwenError(code))

    # --- saving ---------------------------------------------------------------

    def _records(self, item, origin: str, sent: WordValues, new: WordValues, changed) -> list:
        batch, at = cf.new_id(), _iso(self.now())
        return [
            CorrectionRecord(
                id=cf.new_id(),
                batch=batch,
                file=Path(item.source).name,
                group=item.group,
                english=item.english,
                origin_chinese=origin,
                field=name,
                old=sent.get(name),
                new=new.get(name),
                at=at,
            )
            for name in changed
        ]

    def _save(self, account, item, scope, sent, new, fp, changed) -> bool:
        if scope == "shared":
            return self._save_shared(item, sent, new, fp, changed)
        folder = Path(item.source).parent
        name = Path(item.source).name
        if not changed:
            cf.update(folder, lambda data: data.mark_checked(fp))
            return True
        # Compare-and-set (R7): a block edited or removed meanwhile is left alone.
        if not self.word_lists.set_values(account, item.source, item.english, sent, new):
            return False
        records = self._records(item, sent.chinese, sent, new, changed)
        new_fp = cf.fingerprint(name, item.group, item.english, new)

        def record(data):
            data.add_records(records)
            data.mark_checked(new_fp)

        cf.update(folder, record)
        item.origin_chinese = new.chinese  # an own list's file meaning changed
        self._apply(item, new, changed)
        return True

    def _save_shared(self, item, sent, new, fp, changed) -> bool:
        """Set the overlay entry for the word, keyed by its file meaning,
        if its values (file plus overlay) are still those sent (R7)."""
        name = Path(item.source).name
        key = cf.overlay_key(name, item.group, item.english, item.origin_chinese)
        new_fp = cf.fingerprint(name, item.group, item.english, new)
        file_values = _file_values(Path(item.source), item.english, item.origin_chinese)

        def save(data) -> bool:
            if data.overlay.get(key, file_values) != sent:
                return False
            # Loaded before the correction elsewhere: don't send it again.
            data.mark_checked(fp)
            if changed:
                data.overlay[key] = new
                data.add_records(self._records(item, item.origin_chinese, sent, new, changed))
                data.mark_checked(new_fp)
            return True

        if not cf.update(self.shared_dir, save):
            return False
        if changed:
            self._apply(item, new, changed)
        return True

    def _apply(self, item: VocabularyItem, new: WordValues, changed: list[str]) -> None:
        item.ipa, item.chinese, item.pos = new.ipa, new.chinese, list(new.pos)
        with self._lock:
            self._corrected.pop(id(item), None)
            self._corrected[id(item)] = (item, list(changed))
            while len(self._corrected) > _REMEMBERED:
                del self._corrected[next(iter(self._corrected))]

    def corrected_fields(self, item: VocabularyItem) -> list[str]:
        with self._lock:
            entry = self._corrected.get(id(item))
        return list(entry[1]) if entry is not None and entry[0] is item else []

    # --- listing ---------------------------------------------------------------

    def _folders(self, account: Account | None) -> list[tuple[str, Path]]:
        """Where this learner's corrections are: their own lists' folder,
        and the shared folder while they practise the shared sets."""
        folders = []
        own_lists = False
        if self.word_lists is not None and account is not None:
            folders.append(("own", self.word_lists.folder(account)))
            own_lists = self.word_lists.word_source(account) == "own"
        if self.shared_dir is not None and not own_lists:
            folders.append(("shared", self.shared_dir))
        return folders

    def list(self, account: Account | None) -> list[dict]:
        entries = []
        for scope, folder in self._folders(account):
            records = cf.read(folder).records
            batches: dict[str, list[CorrectionRecord]] = {}
            for record in records:
                batches.setdefault(record.batch, []).append(record)
            undoable = {
                batch: self._current(account, scope, folder, members) is not None
                for batch, members in batches.items()
                if all(r.undone_at is None for r in members)
            }
            for record in records:
                entries.append(self._entry(scope, record, undoable.get(record.batch, False)))
        entries.sort(key=lambda e: e["at"], reverse=True)
        return entries[:LIST_LIMIT]

    # --- undo ---------------------------------------------------------------------

    def _current(self, account, scope, folder: Path, batch: list[CorrectionRecord]):
        """The word's values now, if they still hold the batch's new values;
        else None (edited or removed since)."""
        first = batch[0]
        if scope == "shared":
            key = cf.overlay_key(first.file, first.group, first.english, first.origin_chinese)
            candidates = [v for v in [cf.read(folder).overlay.get(key)] if v is not None]
        else:
            candidates = self.word_lists.word_values(account, folder / first.file, first.english)
        for values in candidates:
            if all(values.get(r.field) == r.new for r in batch):
                return values
        return None

    def undo(self, account: Account | None, record_id: str, live_items=()) -> list[str]:
        """Put back the old values of every field changed by the check that
        made *record_id* (its batch), and mark those values checked so the
        change never comes back (FR-005). Returns the fields restored."""
        for scope, folder in self._folders(account):
            records = cf.read(folder).records
            target = next((r for r in records if r.id == record_id), None)
            if target is not None:
                break
        else:
            raise CorrectionNotFound(record_id)
        batch = [r for r in records if r.batch == target.batch]
        if any(r.undone_at is not None for r in batch):
            raise AlreadyUndone(record_id)

        current = self._current(account, scope, folder, batch)
        if current is None:
            raise WordChanged(record_id)
        restored = _with(current, {r.field: r.old for r in batch})
        ids, at = {r.id for r in batch}, _iso(self.now())
        restored_fp = cf.fingerprint(target.file, target.group, target.english, restored)
        key = cf.overlay_key(target.file, target.group, target.english, target.origin_chinese)
        file_values = (
            _file_values(folder / target.file, target.english, target.origin_chinese)
            if scope == "shared"
            else None
        )
        if scope == "own" and not self.word_lists.set_values(
            account, folder / target.file, target.english, current, restored
        ):
            raise WordChanged(record_id)

        def mark(data) -> bool:
            if scope == "shared":
                if any(r.undone_at for r in data.records if r.id in ids):
                    raise AlreadyUndone(record_id)
                if data.overlay.get(key) != current:
                    return False
                if restored == file_values:
                    del data.overlay[key]  # back to the shared file's values
                else:
                    data.overlay[key] = restored
            for record in data.records:
                if record.id in ids:
                    data.replace_record(replace(record, undone_at=at))
            data.mark_checked(restored_fp)
            return True

        if not cf.update(folder, mark):
            raise WordChanged(record_id)
        for item in live_items:
            if (
                item is not None
                and item.source is not None
                and Path(item.source).name == target.file
                and item.english == target.english
                and values_of(item) == current
            ):
                item.ipa, item.chinese, item.pos = (
                    restored.ipa,
                    restored.chinese,
                    list(restored.pos),
                )
                if scope == "own":
                    item.origin_chinese = restored.chinese
                with self._lock:
                    self._corrected.pop(id(item), None)
        return [r.field for r in batch]

    def _entry(self, scope: str, record: CorrectionRecord, can_undo: bool) -> dict:
        return {
            "id": record.id,
            "scope": scope,
            "english": record.english,
            "list": record.file,
            "field": record.field,
            "old": record.old,
            "new": record.new,
            "at": record.at,
            "undone": record.undone_at is not None,
            "can_undo": can_undo,
        }

    def wait_all(self, timeout: float | None = None) -> None:
        with self._lock:
            threads = list(self._threads.values())
        for thread in threads:
            thread.join(timeout)


class BoundCorrections:
    """CorrectionService for one account (or none), as a session uses it."""

    def __init__(self, service: CorrectionService, account: Account | None):
        self.service = service
        self.account = account

    def prepare(self, item: VocabularyItem) -> None:
        self.service.prepare(self.account, item)

    def corrected_fields(self, item: VocabularyItem) -> list[str]:
        return self.service.corrected_fields(item)

    def list(self) -> list[dict]:
        return self.service.list(self.account)

    def paused(self) -> dict | None:
        return self.service.paused()

    def undo(self, record_id: str, live_items=()) -> list[str]:
        return self.service.undo(self.account, record_id, live_items)
