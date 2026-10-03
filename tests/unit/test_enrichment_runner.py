"""Unit tests for EnrichmentRunner (spec 018, data-model.md): a background
worker enriches a pending import's words one by one through an injected
request function, validating every reply before it becomes item data."""

import threading
from pathlib import Path

import pytest

from src.models.account import Account
from src.services.enrichment import (
    EnrichmentRunner,
    PendingImportStore,
    build_import,
)
from src.services.enrichment_client import EnrichmentReply
from src.services.word_lists import DraftWord, ParsedUpload

LILY = Account("lily", "pw", "Lily", Path("p.md"))


def ok(chinese="热心的；热情的", alternates=None):
    return EnrichmentReply(outcome="ok", chinese=chinese, alternates=alternates or [])


class SpyStore(PendingImportStore):
    def __init__(self, root):
        super().__init__(root)
        self.saves = 0

    def save(self, account, pending):
        self.saves += 1
        super().save(account, pending)


def _drafts(*words):
    items = []
    for n, word in enumerate(words, start=1):
        if isinstance(word, DraftWord):
            items.append(word)
        else:
            items.append(DraftWord(word, None, None, [], f"line {n}"))
    return ParsedUpload(items=items)


def _run(tmp_path, words, replies, store=None):
    """Enrich *words* with *replies* (dict english -> reply, or a callable)
    and return (runner, store, calls)."""
    store = store or SpyStore(tmp_path)
    calls = []

    def fake(english, supplied, base_url, model):
        calls.append((english, dict(supplied)))
        if callable(replies):
            return replies(english)
        return replies[english]

    runner = EnrichmentRunner(store, "http://ollama", "m", request_fn=fake)
    runner.begin(LILY, build_import("z-words", "z-words.txt", _drafts(*words)))
    runner.wait(LILY, 5)
    return runner, store, calls


def test_items_enriched_in_order_and_saved_each_time(tmp_path):
    progress = []
    runner_box = {}

    def reply(english):
        progress.append(runner_box["r"].get(LILY).done)
        return ok(chinese="中文")

    store = SpyStore(tmp_path)
    calls = []

    def fake(english, supplied, base_url, model):
        calls.append(english)
        return reply(english)

    runner = EnrichmentRunner(store, "http://ollama", "m", request_fn=fake)
    runner_box["r"] = runner
    runner.begin(LILY, build_import("z-words", "z-words.txt", _drafts("zealous", "tyre", "arduous")))
    runner.wait(LILY, 5)

    pending = runner.get(LILY)
    assert calls == ["zealous", "tyre", "arduous"]
    assert progress == [0, 1, 2]
    assert [i.state for i in pending.items] == ["enriched"] * 3
    assert pending.status == "completed"
    assert store.saves >= 3
    assert store.load(LILY) == pending


def test_supplied_chinese_is_kept_and_sent_as_context(tmp_path):
    draft = DraftWord("receive", "收到", None, [], "line 1")
    runner, _, calls = _run(tmp_path, [draft], {"receive": ok(chinese="接收")})
    item = runner.get(LILY).items[0]
    assert calls == [("receive", {"chinese": "收到", "alternates": []})]
    assert item.chinese == "收到"
    assert item.ipa == "rəˈsiːv"  # from the offline dictionary


def test_fully_supplied_word_makes_no_request(tmp_path):
    draft = DraftWord("receive", "收到", "rɪˈsiːv", ["accept"], "line 1")
    runner, _, calls = _run(tmp_path, [draft], {})
    item = runner.get(LILY).items[0]
    assert calls == []
    assert (item.state, item.chinese, item.ipa, item.alternates) == (
        "enriched",
        "收到",
        "rɪˈsiːv",
        ["accept"],
    )


def test_model_alternates_are_filtered(tmp_path):
    runner, _, _ = _run(
        tmp_path, ["tyre"], {"tyre": ok(chinese="轮胎", alternates=["tire", "wheel"])}
    )
    item = runner.get(LILY).items[0]
    assert item.alternates == ["tire"]
    assert item.dropped_alternates == ["wheel"]


def test_ipa_comes_from_the_dictionary(tmp_path):
    runner, _, _ = _run(tmp_path, ["zealous"], {"zealous": ok()})
    item = runner.get(LILY).items[0]
    assert item.ipa == "ˈzeləs"
    assert item.ipa_review is None


def test_unknown_pronunciation_marks_review_but_keeps_word(tmp_path):
    runner, _, _ = _run(tmp_path, ["zxqvword"], {"zxqvword": ok()})
    item = runner.get(LILY).items[0]
    assert item.state == "enriched"
    assert item.ipa is None
    assert item.ipa_review == "not in the pronunciation dictionary"


def test_bad_chinese_fails_the_item(tmp_path):
    runner, _, _ = _run(tmp_path, ["zealous", "tyre"], {"zealous": ok(chinese="hello"), "tyre": ok()})
    first, second = runner.get(LILY).items
    assert (first.state, first.error) == ("failed", "meaning was unusable")
    assert first.chinese is None
    assert second.state == "enriched"
    assert runner.get(LILY).status == "partially_failed"


def test_english_is_never_changed(tmp_path):
    runner, _, _ = _run(tmp_path, ["  zealous"], {"  zealous": ok()})
    assert runner.get(LILY).items[0].english == "  zealous"


def test_duplicates_are_not_sent(tmp_path):
    runner, _, calls = _run(tmp_path, ["zealous", "Zealous "], lambda _w: ok())
    pending = runner.get(LILY)
    assert [c[0] for c in calls] == ["zealous"]
    assert pending.items[1].state == "duplicate"
    assert pending.items[1].duplicate_of == 0
    assert pending.total == 1


def test_wait_returns_when_idle(tmp_path):
    runner = EnrichmentRunner(PendingImportStore(tmp_path), "u", "m", request_fn=lambda *a: ok())
    assert runner.wait(LILY, 0.1) is True
    assert runner.get(LILY) is None


@pytest.fixture
def gate():
    event = threading.Event()
    yield event
    event.set()


# --- US2: failures never lose the upload --------------------------------------

UNAVAILABLE = "Local AI unavailable — start Ollama, then press Retry."


def test_bad_reply_fails_only_that_item(tmp_path):
    replies = {w: ok() for w in ("a1", "a3", "a4")}
    replies["a2"] = EnrichmentReply(outcome="bad_reply", detail="bad_status")
    runner, _, _ = _run(tmp_path, ["a1", "a2", "a3", "a4"], replies)
    pending = runner.get(LILY)
    assert [i.state for i in pending.items] == ["enriched", "failed", "enriched", "enriched"]
    assert pending.items[1].error == "the local AI gave an unusable answer"
    assert pending.status == "partially_failed"


def test_unavailable_stops_the_batch_and_keeps_words_waiting(tmp_path):
    def reply(english):
        return EnrichmentReply(outcome="unavailable") if english == "a3" else ok()

    runner, store, calls = _run(tmp_path, ["a1", "a2", "a3", "a4", "a5"], reply)
    pending = runner.get(LILY)
    assert [c[0] for c in calls] == ["a1", "a2", "a3"]
    assert [i.state for i in pending.items] == ["enriched", "enriched", "waiting", "waiting", "waiting"]
    assert pending.status == "failed"
    assert pending.failure_reason == UNAVAILABLE
    assert store.load(LILY) == pending


def test_retry_all_failed_keeps_enriched_untouched(tmp_path):
    attempts = {"a2": 0}

    def reply(english):
        if english == "a2":
            attempts["a2"] += 1
            if attempts["a2"] == 1:
                return EnrichmentReply(outcome="bad_reply", detail="x")
        return ok(chinese=f"中{english}")

    runner, _, calls = _run(tmp_path, ["a1", "a2", "a3"], reply)
    before = runner.get(LILY).items[0]
    snapshot = (before.chinese, before.ipa, before.alternates)

    assert runner.retry(LILY) is not None
    runner.wait(LILY, 5)
    pending = runner.get(LILY)
    assert [c[0] for c in calls] == ["a1", "a2", "a3", "a2"]
    assert [i.state for i in pending.items] == ["enriched"] * 3
    assert pending.items[1].error is None
    assert (pending.items[0].chinese, pending.items[0].ipa, pending.items[0].alternates) == snapshot
    assert pending.status == "completed"


def test_retry_after_unavailable_resumes(tmp_path):
    state = {"down": True}

    def reply(english):
        if state["down"] and english == "a2":
            return EnrichmentReply(outcome="unavailable")
        return ok()

    runner, _, calls = _run(tmp_path, ["a1", "a2", "a3"], reply)
    state["down"] = False
    runner.retry(LILY)
    runner.wait(LILY, 5)
    pending = runner.get(LILY)
    assert [c[0] for c in calls] == ["a1", "a2", "a2", "a3"]
    assert pending.status == "completed"
    assert pending.failure_reason is None


def test_retry_single_item(tmp_path):
    bad = EnrichmentReply(outcome="bad_reply", detail="x")
    runner, _, _ = _run(tmp_path, ["a1", "a2", "a3"], {"a1": bad, "a2": ok(), "a3": bad})
    runner.request_fn = lambda english, *_: ok()
    runner.retry(LILY, index=2)
    runner.wait(LILY, 5)
    assert [i.state for i in runner.get(LILY).items] == ["failed", "enriched", "enriched"]
    with pytest.raises(ValueError):
        runner.retry(LILY, index=1)
    with pytest.raises(ValueError):
        runner.retry(LILY, index=9)


def _blocking_runner(tmp_path, gate, words=("a1", "a2")):
    store = SpyStore(tmp_path)
    started = threading.Event()
    calls = []

    def fake(english, supplied, base_url, model):
        calls.append(english)
        started.set()
        gate.wait(5)
        return ok()

    runner = EnrichmentRunner(store, "u", "m", request_fn=fake)
    runner.begin(LILY, build_import("z", "z.txt", _drafts(*words)))
    assert started.wait(5)
    return runner, store, calls


def test_no_second_worker_while_running(tmp_path, gate):
    runner, _, calls = _blocking_runner(tmp_path, gate)
    assert runner.start(LILY) is None
    assert runner.retry(LILY) is None
    gate.set()
    runner.wait(LILY, 5)
    assert calls == ["a1", "a2"]


def test_cancel_stops_without_saving(tmp_path, gate):
    runner, store, calls = _blocking_runner(tmp_path, gate)
    saves_before = store.saves
    runner.cancel(LILY)
    gate.set()
    runner.wait(LILY, 5)
    assert calls == ["a1"]
    assert store.saves == saves_before


def test_interrupted_import_resumes_on_retry(tmp_path, gate):
    runner, _, _ = _blocking_runner(tmp_path, gate, words=("a1", "a2", "a3"))
    runner.cancel(LILY)
    gate.set()
    runner.wait(LILY, 5)

    calls = []
    fresh = EnrichmentRunner(
        PendingImportStore(tmp_path), "u", "m",
        request_fn=lambda english, *_: calls.append(english) or ok(),
    )
    assert fresh.get(LILY).status == "interrupted"
    fresh.retry(LILY)
    fresh.wait(LILY, 5)
    assert calls == ["a1", "a2", "a3"]
    assert fresh.get(LILY).status == "completed"
