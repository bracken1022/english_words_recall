"""Local-AI enrichment of uploaded word lists (spec 018, data-model.md).

An upload becomes a PendingImport: the extracted words, kept per account in
word-lists/<username>/.pending-import.json until the learner confirms or
discards it (contracts/pending-import-file.md). The model's replies are
untrusted; only the validators here turn them into item fields, and
nothing reaches a vocabulary file until the learner confirms."""

import json
import logging
import os
import re
import tempfile
import threading
from collections.abc import Callable
from dataclasses import asdict, dataclass, field, fields
from datetime import UTC, datetime
from pathlib import Path

from src.lib.alternates import filter_alternates, is_spelling_variant
from src.lib.ipa import check_american_ipa, is_heteronym, normalize_ipa
from src.lib.markdown_blocks import parse_blocks
from src.lib.pos import normalize_pos, strip_pos_notes
from src.lib.us_pronunciation import lookup_american_ipa
from src.models.account import Account
from src.services.enrichment_client import EnrichmentReply, request_enrichment
from src.services.word_lists import ParsedUpload, WordListStore

log = logging.getLogger(__name__)

PENDING_FILENAME = ".pending-import.json"
FILE_VERSION = 1
MAX_API_SKIPPED = 20

STATUSES = ("running", "completed", "partially_failed", "failed", "interrupted")
ITEM_STATES = ("waiting", "enriching", "enriched", "failed", "duplicate")

UNAVAILABLE_MESSAGE = "Local AI unavailable — start Ollama, then press Retry."
BAD_REPLY_MESSAGE = "the local AI gave an unusable answer"

MAX_CHINESE_LENGTH = 40
MAX_CHINESE_PARTS = 4
UNUSABLE_MEANING = "meaning was unusable"


@dataclass
class ImportItem:
    english: str
    position: str
    supplied: dict
    state: str = "waiting"
    ipa: str | None = None
    ipa_review: str | None = None
    chinese: str | None = None
    alternates: list[str] = field(default_factory=list)
    dropped_alternates: list[str] = field(default_factory=list)
    error: str | None = None
    existing: dict | None = None
    choice: str = "keep"
    duplicate_of: int | None = None
    # Spec 019; defaults keep older pending-import files loadable.
    pos: list[str] = field(default_factory=list)
    pos_review: str | None = None

    def reset(self) -> None:
        """Back to waiting, dropping any earlier result (for a retry)."""
        self.state, self.error = "waiting", None
        self.ipa = self.ipa_review = self.chinese = self.pos_review = None
        self.alternates, self.dropped_alternates, self.pos = [], [], []

    @property
    def is_own_existing(self) -> bool:
        return bool(self.existing) and self.existing.get("source") == "own"


@dataclass
class PendingImport:
    list_name: str
    source_filename: str
    created_at: str
    status: str
    items: list[ImportItem]
    failure_reason: str | None = None
    upload_skipped: list[str] = field(default_factory=list)
    version: int = FILE_VERSION

    @property
    def total(self) -> int:
        return sum(1 for item in self.items if item.state != "duplicate")

    @property
    def done(self) -> int:
        return sum(1 for item in self.items if item.state in ("enriched", "failed"))

    @property
    def enriched_count(self) -> int:
        return sum(1 for item in self.items if item.state == "enriched")

    @property
    def failed_count(self) -> int:
        return sum(1 for item in self.items if item.state == "failed")

    @property
    def savable(self) -> list[ImportItem]:
        """Enriched words that go into the new list. Own-list existing
        entries never do: they are kept, or updated in place (updates)."""
        return [i for i in self.items if i.state == "enriched" and not i.is_own_existing]

    @property
    def left_out_count(self) -> int:
        """Words neither saved nor used to update an entry (failed,
        waiting, or existing entries kept as they are)."""
        used = {id(i) for i in self.savable} | {id(i) for i in self.updates}
        return sum(1 for i in self.items if i.state != "duplicate" and id(i) not in used)

    def update_map(self) -> dict[str, list[tuple[str, dict]]]:
        """The confirmed updates grouped by list, for WordListStore."""
        grouped: dict[str, list[tuple[str, dict]]] = {}
        for item in self.updates:
            fields_ = {
                "ipa": item.ipa,
                "pos": list(item.pos),
                "chinese": item.chinese,
                "alternates": list(item.alternates),
            }
            grouped.setdefault(item.existing["list"], []).append((item.english, fields_))
        return grouped

    @property
    def updates(self) -> list[ImportItem]:
        return [
            i
            for i in self.items
            if i.state == "enriched" and i.is_own_existing and i.choice == "update"
        ]

    def to_api(self) -> dict:
        return {
            "list_name": self.list_name,
            "source_filename": self.source_filename,
            "status": self.status,
            "failure_reason": self.failure_reason,
            "total": self.total,
            "done": self.done,
            "enriched_count": self.enriched_count,
            "failed_count": self.failed_count,
            "savable_count": len(self.savable),
            "upload_skipped": self.upload_skipped[:MAX_API_SKIPPED],
            "upload_skipped_count": len(self.upload_skipped),
            "items": [
                {
                    "index": index,
                    "english": item.english,
                    "state": item.state,
                    "ipa": item.ipa,
                    "ipa_review": item.ipa_review,
                    "chinese": item.chinese,
                    "alternates": item.alternates,
                    "dropped_alternates": item.dropped_alternates,
                    "error": item.error,
                    "existing": item.existing,
                    "choice": item.choice,
                    "duplicate_of": item.duplicate_of,
                    "pos": item.pos,
                    "pos_review": item.pos_review,
                }
                for index, item in enumerate(self.items)
            ],
        }

    def to_json(self) -> dict:
        data = asdict(self)
        return {"version": data.pop("version"), **data}

    @classmethod
    def from_json(cls, data: dict) -> "PendingImport":
        if not isinstance(data, dict) or data.get("version") != FILE_VERSION:
            raise ValueError("unsupported pending import file")
        item_keys = {f.name for f in fields(ImportItem)}
        items = [ImportItem(**{k: v for k, v in raw.items() if k in item_keys}) for raw in data["items"]]
        return cls(
            list_name=data["list_name"],
            source_filename=data["source_filename"],
            created_at=data["created_at"],
            status=data["status"],
            items=items,
            failure_reason=data.get("failure_reason"),
            upload_skipped=list(data.get("upload_skipped") or []),
        )


# --- validation (contracts/enrichment-validation.md) ------------------------

_CJK = re.compile(r"[一-鿿]")
_POS_LABEL = re.compile(r"\b(?:n|v|vt|vi|adj|adv|prep)\.")
_LATIN_RUN = re.compile(r"[A-Za-z]+(?:\s+[A-Za-z]+){3,}")


def validate_chinese(text) -> tuple[str | None, str | None]:
    """Return (meaning, None) with separators normalised to "；", or
    (None, UNUSABLE_MEANING) when it isn't a concise study meaning."""
    if not isinstance(text, str) or "\n" in text.strip() or "\r" in text:
        return None, UNUSABLE_MEANING
    # The part of speech has its own field now (spec 019, FR-008).
    text = strip_pos_notes(text)
    parts = [part.strip() for part in re.split(r"[;；,，]", text.strip())]
    meaning = "；".join(parts)
    if (
        not meaning
        or not _CJK.search(meaning)
        or len(parts) > MAX_CHINESE_PARTS
        or any(not part for part in parts)
        or len(meaning) > MAX_CHINESE_LENGTH
        or _POS_LABEL.search(meaning)
        or "【" in meaning
        or "】" in meaning
        or _LATIN_RUN.search(meaning)
    ):
        return None, UNUSABLE_MEANING
    return meaning, None


def validate_item(item: ImportItem, reply: EnrichmentReply | None) -> None:
    """Turn an untrusted model *reply* (None when every field was supplied)
    into the item's fields, per contracts/enrichment-validation.md. The
    English text is never touched. Leaves the item "enriched", or "failed"
    with an error when no usable Chinese meaning results."""
    supplied = item.supplied
    item.error = None

    if supplied.get("chinese"):
        chinese = supplied["chinese"]
    else:
        chinese, problem = validate_chinese(reply.chinese if reply else None)
        if problem:
            item.reset()
            item.state, item.error = "failed", problem
            return
    item.chinese = chinese
    item.alternates, item.dropped_alternates = filter_alternates(
        item.english, list(supplied.get("alternates") or []), reply.alternates if reply else []
    )
    item.ipa, item.ipa_review = _resolve_ipa(item)
    item.pos, item.pos_review = _resolve_pos(item, reply)
    item.state = "enriched"


def _resolve_pos(item: ImportItem, reply: EnrichmentReply | None) -> tuple[list[str], str | None]:
    """(pos, pos_review) by contracts/enrichment-pos-delta.md: the learner's
    labels; else the model's first label, if every label it gave is a
    known one; else review."""
    if item.supplied.get("pos"):
        return list(item.supplied["pos"]), None
    labels, _problem = normalize_pos(reply.pos if reply else None)
    if labels:
        # Only the first generated label is kept: the local model tends to
        # add classes the meanings don't support (spec 019 eval-report.md).
        return labels[:1], None
    return [], "part of speech needs review"


def _resolve_ipa(item: ImportItem) -> tuple[str | None, str | None]:
    """(ipa, ipa_review), by the first matching rule of the IPA table in
    contracts/enrichment-validation.md. Pronunciations come from the offline
    American dictionary, never the model; a doubtful one is flagged for
    review, never guessed (FR-009)."""
    if item.supplied.get("ipa"):
        return item.supplied["ipa"], None
    if not any(ch.islower() for ch in item.english):
        return None, "abbreviation — check how it's said"
    if is_heteronym(item.english):
        return None, "pronunciation depends on the meaning"
    variants = [a for a in item.alternates if is_spelling_variant(item.english.strip(), a)]
    found = lookup_american_ipa(item.english, variants)
    if found.ambiguous:
        return None, "more than one pronunciation — check which one you need"
    if found.ipa is None:
        return None, "not in the pronunciation dictionary"
    problems = check_american_ipa(found.ipa)
    if problems:
        return None, f"dictionary pronunciation failed check: {problems[0]}"
    return found.ipa, None


def _key(english: str) -> str:
    return english.strip().casefold()


def _existing_entry(source: str, list_name: str, block: dict) -> dict:
    ipa, _problem = normalize_ipa(block.get("ipa"))
    alternates = block.get("alternates")
    pos, _pos_problem = normalize_pos(block.get("pos"))
    entry = {
        "source": source,
        "list": list_name,
        "ipa": ipa,
        "chinese": block.get("chinese") if isinstance(block.get("chinese"), str) else None,
        "alternates": [a for a in alternates if isinstance(a, str)]
        if isinstance(alternates, list)
        else [],
    }
    if pos:
        entry["pos"] = pos  # only when stored (spec 019)
    return entry


def existing_lookup_for(
    store: WordListStore, account: Account, shared_dir: Path
) -> Callable[[str], dict | None]:
    """Look words up in the account's current vocabulary (research R7):
    its own lists, or the shared folder while it has none. Matching
    ignores case and surrounding spaces; the first occurrence wins."""
    entries: dict[str, dict] = {}
    own = store.word_source(account) == "own"
    folder = store.folder(account) if own else shared_dir
    paths = sorted(folder.glob("*.md")) if folder.is_dir() else []
    for path in paths:
        blocks, _warnings = parse_blocks(path.read_text(encoding="utf-8"))
        for block in blocks:
            english = block.get("english")
            if not isinstance(english, str) or not english.strip():
                continue
            if own:
                entry = _existing_entry("own", path.stem, block)
            else:
                group = block.get("group")
                entry = _existing_entry("shared", group if isinstance(group, str) else path.stem, block)
            entries.setdefault(_key(english), entry)
    return lambda english: entries.get(_key(english))


def build_import(
    list_name: str,
    source_filename: str,
    parsed: ParsedUpload,
    existing_lookup: Callable[[str], dict | None] = lambda _english: None,
) -> PendingImport:
    """A new pending import from parsed DraftWords: repeated words are
    marked as duplicates, and existing entries are looked up per word."""
    items: list[ImportItem] = []
    first_index: dict[str, int] = {}
    for draft in parsed.items:
        supplied: dict = {"alternates": list(draft.alternates)}
        if draft.chinese:
            supplied["chinese"] = draft.chinese
        if draft.ipa:
            supplied["ipa"] = draft.ipa
        if draft.pos:
            supplied["pos"] = list(draft.pos)
        item = ImportItem(english=draft.english, position=draft.position, supplied=supplied)
        key = _key(draft.english)
        if key in first_index:
            item.state, item.duplicate_of = "duplicate", first_index[key]
        else:
            first_index[key] = len(items)
            item.existing = existing_lookup(draft.english)
        items.append(item)
    return PendingImport(
        list_name=list_name,
        source_filename=source_filename,
        created_at=datetime.now(UTC).isoformat(timespec="seconds"),
        status="running",
        items=items,
        upload_skipped=list(parsed.skipped),
    )


# --- persistence (contracts/pending-import-file.md) -------------------------


class PendingImportStore:
    def __init__(self, root: Path):
        self.root = root
        self._locks: dict[str, threading.Lock] = {}
        self._locks_guard = threading.Lock()

    def lock(self, account: Account) -> threading.Lock:
        with self._locks_guard:
            return self._locks.setdefault(account.username, threading.Lock())

    def path(self, account: Account) -> Path:
        return self.root / account.username / PENDING_FILENAME

    def save(self, account: Account, pending: PendingImport) -> None:
        target = self.path(account)
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=target.parent, suffix=".tmp", delete=False
        ) as tmp:
            json.dump(pending.to_json(), tmp, ensure_ascii=False, indent=2)
        try:
            os.replace(tmp.name, target)
        except BaseException:
            Path(tmp.name).unlink(missing_ok=True)
            raise

    def load(self, account: Account) -> PendingImport | None:
        target = self.path(account)
        if not target.exists():
            return None
        try:
            pending = PendingImport.from_json(json.loads(target.read_text(encoding="utf-8")))
        except (ValueError, KeyError, TypeError):
            stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
            broken = target.with_name(f".pending-import.broken-{stamp}.json")
            target.rename(broken)
            log.warning("Unreadable pending import for %s moved to %s", account.username, broken)
            return None
        if pending.status == "running":
            # The worker that owned it died with the old process.
            pending.status = "interrupted"
            for item in pending.items:
                if item.state == "enriching":
                    item.state = "waiting"
            self.save(account, pending)
        return pending

    def delete(self, account: Account) -> None:
        self.path(account).unlink(missing_ok=True)


def with_pos(
    item: ImportItem,
    reply: EnrichmentReply,
    pos_request_fn: Callable[..., EnrichmentReply],
    base_url: str,
    model: str,
) -> EnrichmentReply:
    """Spec 019: once the meaning is known, ask for the part of speech in
    its own request. An unavailable model makes the whole word wait; any
    other failure leaves the labels empty, so the word is marked for
    review. Supplied labels need no request."""
    if reply.outcome != "ok" or item.supplied.get("pos"):
        return reply
    chinese = item.supplied.get("chinese") or validate_chinese(reply.chinese)[0]
    if not chinese:
        return reply
    pos_reply = pos_request_fn(item.english, chinese, base_url, model)
    if pos_reply.outcome == "unavailable":
        return pos_reply
    reply.pos = pos_reply.pos if pos_reply.outcome == "ok" else []
    return reply


# --- background enrichment ---------------------------------------------------


class EnrichmentRunner:
    """Enriches each account's pending import on a background thread, one
    word at a time, so progress is exact and requests never block. At most
    one worker runs per account (FR-020). The in-memory import is the
    source of truth while this process runs; every change is saved."""

    def __init__(
        self,
        pending_store: PendingImportStore,
        base_url: str,
        model: str,
        request_fn: Callable[..., EnrichmentReply] = request_enrichment,
        pos_request_fn: Callable[..., EnrichmentReply] | None = None,
    ):
        self.store = pending_store
        self.base_url = base_url
        self.model = model
        self.request_fn = request_fn
        # Spec 019: the part-of-speech request (request_pos in the app);
        # None leaves part of speech to the upload, or to review.
        self.pos_request_fn = pos_request_fn
        self._pending: dict[str, PendingImport | None] = {}
        self._threads: dict[str, threading.Thread] = {}
        self._cancel: dict[str, threading.Event] = {}

    def lock(self, account: Account) -> threading.Lock:
        return self.store.lock(account)

    def current(self, account: Account) -> PendingImport | None:
        """The account's import; the caller holds lock(account). The first
        read in this process loads the file, which turns an import left
        "running" by a previous process into "interrupted"."""
        if account.username not in self._pending:
            self._pending[account.username] = self.store.load(account)
        return self._pending[account.username]

    def get(self, account: Account) -> PendingImport | None:
        with self.lock(account):
            return self.current(account)

    def state(self, account: Account) -> dict | None:
        with self.lock(account):
            pending = self.current(account)
            return pending.to_api() if pending else None

    def is_running(self, account: Account) -> bool:
        thread = self._threads.get(account.username)
        return thread is not None and thread.is_alive()

    def begin(self, account: Account, pending: PendingImport) -> threading.Thread | None:
        """Make *pending* the account's import (replacing any other) and
        start enriching it."""
        with self.lock(account):
            self._pending[account.username] = pending
            self.store.save(account, pending)
        return self.start(account)

    def start(self, account: Account) -> threading.Thread | None:
        with self.lock(account):
            if self.is_running(account):
                return None
            pending = self.current(account)
            if pending is None:
                return None
            pending.status = "running"
            pending.failure_reason = None
            self.store.save(account, pending)
            cancel = threading.Event()
            self._cancel[account.username] = cancel
            thread = threading.Thread(
                target=self._work, args=(account, pending, cancel), daemon=True
            )
            self._threads[account.username] = thread
            thread.start()
            return thread

    def retry(self, account: Account, index: int | None = None) -> threading.Thread | None:
        """Retry one failed word (*index*), or every failed word plus any
        still waiting. Returns None while a worker is already running.
        Raises KeyError with no import, ValueError for a bad *index*."""
        with self.lock(account):
            if self.is_running(account):
                return None
            pending = self.current(account)
            if pending is None:
                raise KeyError(account.username)
            if index is not None:
                if (
                    not isinstance(index, int)
                    or isinstance(index, bool)
                    or not 0 <= index < len(pending.items)
                    or pending.items[index].state != "failed"
                ):
                    raise ValueError(index)
                pending.items[index].reset()
            else:
                for item in pending.items:
                    if item.state == "failed":
                        item.reset()
        return self.start(account)

    def wait(self, account: Account, timeout: float | None = None) -> bool:
        """Join the account's worker; True once nothing is running."""
        thread = self._threads.get(account.username)
        if thread is not None:
            thread.join(timeout)
        return not self.is_running(account)

    def cancel(self, account: Account) -> None:
        event = self._cancel.get(account.username)
        if event is not None:
            event.set()

    def set_choice(self, account: Account, index, choice) -> None:
        """Keep or update an existing own-list entry (FR-017). Raises
        KeyError with no import, ValueError when the word has no entry."""
        with self.lock(account):
            pending = self.current(account)
            if pending is None:
                raise KeyError(account.username)
            if (
                not isinstance(index, int)
                or isinstance(index, bool)
                or not 0 <= index < len(pending.items)
                or not pending.items[index].is_own_existing
                or choice not in ("keep", "update")
            ):
                raise ValueError(index)
            pending.items[index].choice = choice
            self.store.save(account, pending)

    def forget(self, account: Account) -> None:
        """Delete the import after it was saved; caller holds the lock."""
        self._pending[account.username] = None
        self.store.delete(account)

    def discard(self, account: Account) -> bool:
        """Stop any worker and delete the import; False if there was none."""
        self.cancel(account)
        self.wait(account, 10)
        with self.lock(account):
            existed = self.current(account) is not None
            self.forget(account)
            return existed

    def _with_pos(self, item: ImportItem, reply: EnrichmentReply) -> EnrichmentReply:
        if self.pos_request_fn is None:
            return reply
        return with_pos(item, reply, self.pos_request_fn, self.base_url, self.model)

    def _work(self, account: Account, pending: PendingImport, cancel: threading.Event) -> None:
        lock = self.lock(account)
        for item in pending.items:
            if item.state != "waiting":
                continue
            with lock:
                if cancel.is_set():
                    return
                item.state = "enriching"
                self.store.save(account, pending)

            reply = None
            # The model supplies the meaning and alternates, then (in a
            # separate request) the part of speech; IPA always comes from
            # the dictionary (spec 018 R4, spec 019).
            if not (item.supplied.get("chinese") and item.supplied.get("pos")):
                reply = self.request_fn(item.english, item.supplied, self.base_url, self.model)
                reply = self._with_pos(item, reply)

            with lock:
                if cancel.is_set():
                    return
                if reply is not None and reply.outcome == "unavailable":
                    # Stop the batch: the remaining words wait for Retry.
                    item.state = "waiting"
                    pending.status = "failed"
                    pending.failure_reason = UNAVAILABLE_MESSAGE
                    self.store.save(account, pending)
                    return
                if reply is not None and reply.outcome != "ok":
                    item.reset()
                    item.state, item.error = "failed", BAD_REPLY_MESSAGE
                else:
                    validate_item(item, reply)
                self.store.save(account, pending)

        with lock:
            if cancel.is_set():
                return
            pending.status = "partially_failed" if pending.failed_count else "completed"
            self.store.save(account, pending)
