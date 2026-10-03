"""Contract tests for contracts/pending-import-file.md (spec 018): one
hidden JSON file per account holds an unconfirmed import, survives
restarts, is written atomically, and is invisible to the vocabulary
loaders and word-list store."""

import json
import os
from pathlib import Path

import pytest

from src.models.account import Account
from src.services.enrichment import ImportItem, PendingImport, PendingImportStore
from src.services.vocabulary_loader import load_vocabulary
from src.services.word_lists import WordListStore

LILY = Account("lily", "pw", "Lily", Path("p.md"))
WEIBO = Account("weibo", "pw", "Weibo", Path("p.md"))


def _pending(status="completed", items=None) -> PendingImport:
    return PendingImport(
        list_name="z-words",
        source_filename="z-words.txt",
        created_at="2026-10-03T09:15:00+00:00",
        status=status,
        failure_reason=None,
        upload_skipped=["line 7: no English word"],
        items=items
        if items is not None
        else [
            ImportItem(
                english="zealous",
                position="line 1",
                supplied={},
                state="enriched",
                ipa="ˈzeləs",
                chinese="热心的；热情的",
                dropped_alternates=["enthusiastic"],
            ),
            ImportItem(
                english="receive",
                position="line 2",
                supplied={"chinese": "收到"},
                state="failed",
                error="the local AI gave an unusable answer",
                existing={
                    "source": "own",
                    "list": "unit1",
                    "ipa": "rɪˈsiːv",
                    "chinese": "收到",
                    "alternates": ["accept"],
                },
                choice="update",
            ),
            ImportItem(
                english="zealous", position="line 3", supplied={}, state="duplicate", duplicate_of=0
            ),
        ],
    )


def test_round_trip_and_location(tmp_path: Path):
    store = PendingImportStore(tmp_path)
    pending = _pending()
    store.save(LILY, pending)

    path = tmp_path / "lily" / ".pending-import.json"
    assert store.path(LILY) == path
    raw = path.read_text(encoding="utf-8")
    assert "热心的" in raw  # ensure_ascii=False
    data = json.loads(raw)
    assert data["version"] == 1
    for derived in ("total", "done", "enriched_count", "failed_count"):
        assert derived not in data

    assert store.load(LILY) == pending


def test_atomic_write_keeps_previous_file(tmp_path: Path, monkeypatch):
    store = PendingImportStore(tmp_path)
    store.save(LILY, _pending())
    before = store.path(LILY).read_bytes()

    def boom(*_args, **_kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError):
        store.save(LILY, _pending(status="failed"))
    assert store.path(LILY).read_bytes() == before
    assert list((tmp_path / "lily").glob("*.tmp")) == []


def test_running_import_loads_as_interrupted(tmp_path: Path):
    store = PendingImportStore(tmp_path)
    items = [
        ImportItem(english="zealous", position="line 1", supplied={}, state="enriched",
                   ipa="ˈzeləs", chinese="热心的"),
        ImportItem(english="tyre", position="line 2", supplied={}, state="enriching"),
        ImportItem(english="arduous", position="line 3", supplied={}, state="waiting"),
    ]
    store.save(LILY, _pending(status="running", items=items))

    loaded = store.load(LILY)
    assert loaded.status == "interrupted"
    assert [i.state for i in loaded.items] == ["enriched", "waiting", "waiting"]
    on_disk = json.loads(store.path(LILY).read_text(encoding="utf-8"))
    assert on_disk["status"] == "interrupted"
    assert on_disk["items"][1]["state"] == "waiting"


@pytest.mark.parametrize("content", ["{", json.dumps({"version": 2, "items": []}), "[]"])
def test_unreadable_file_is_quarantined(tmp_path: Path, content):
    store = PendingImportStore(tmp_path)
    folder = tmp_path / "lily"
    folder.mkdir()
    (folder / ".pending-import.json").write_text(content, encoding="utf-8")

    assert store.load(LILY) is None
    assert not (folder / ".pending-import.json").exists()
    broken = list(folder.glob(".pending-import.broken-*.json"))
    assert len(broken) == 1
    assert broken[0].read_text(encoding="utf-8") == content


def test_delete_and_missing(tmp_path: Path):
    store = PendingImportStore(tmp_path)
    assert store.load(LILY) is None
    store.save(LILY, _pending())
    store.delete(LILY)
    assert not store.path(LILY).exists()
    assert store.load(LILY) is None
    store.delete(LILY)  # deleting nothing is fine


def test_invisible_to_word_lists_and_loader(tmp_path: Path):
    PendingImportStore(tmp_path).save(LILY, _pending())
    word_lists = WordListStore(tmp_path)
    assert word_lists.list(LILY) == []
    assert word_lists.word_source(LILY) == "shared"
    assert load_vocabulary(tmp_path / "lily") == ([], [])


def test_accounts_are_isolated(tmp_path: Path):
    store = PendingImportStore(tmp_path)
    store.save(LILY, _pending())
    assert store.load(WEIBO) is None
    assert not (tmp_path / "weibo" / ".pending-import.json").exists()
