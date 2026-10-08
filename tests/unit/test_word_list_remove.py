"""Tests for removing and restoring one word in a learner's own list file,
and for hiding shared words per learner (spec 020, research R2/R3)."""

import hashlib
import json
from pathlib import Path

import pytest

from src.models.account import Account
from src.models.vocabulary_item import VocabularyItem
from src.services.vocabulary_loader import load_vocabulary
from src.services.word_lists import RemovedEntry, WordListStore

LILY = Account("lily", "pw", "Lily", Path("p.md"))
WEIBO = Account("weibo", "pw", "Weibo", Path("p.md"))
WORDS = [
    VocabularyItem("zealous", "热心的", ipa="ˈzeləs", pos=["adj."]),
    VocabularyItem("rent", "租金；出租", pos=["n.", "v."]),
    VocabularyItem("tyre", "轮胎", ["tire"]),
]


@pytest.fixture
def setup(tmp_path):
    store = WordListStore(tmp_path / "word-lists")
    store.save(LILY, "unit1", WORDS)
    return store, store.folder(LILY) / "unit1.md"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize("index", [0, 1, 2])
def test_cut_removes_only_that_entry(setup, index):
    store, path = setup
    before = path.read_text(encoding="utf-8")
    word = WORDS[index]
    removed = store.remove_word(LILY, path, word.english, word.chinese)
    after = path.read_text(encoding="utf-8")
    assert isinstance(removed, RemovedEntry)
    assert before.replace(removed.text, "", 1) == after
    assert "\n\n\n" not in after
    assert not after.startswith("\n")
    items, warnings = load_vocabulary(path.parent)
    assert warnings == []
    assert [i.english for i in items] == [w.english for w in WORDS if w is not word]


@pytest.mark.parametrize("index", [0, 1, 2])
def test_restore_is_byte_identical(setup, index):
    store, path = setup
    digest = sha(path)
    removed = store.remove_word(LILY, path, WORDS[index].english, WORDS[index].chinese)
    store.restore_word(LILY, removed)
    assert sha(path) == digest


def test_restore_after_file_changed_keeps_everything(setup):
    store, path = setup
    first = store.remove_word(LILY, path, "zealous", "热心的")
    store.remove_word(LILY, path, "rent", "租金；出租")
    store.restore_word(LILY, first)
    items, warnings = load_vocabulary(path.parent)
    assert warnings == []
    assert sorted(i.english for i in items) == ["tyre", "zealous"]


def test_only_first_duplicate_removed(tmp_path):
    store = WordListStore(tmp_path / "word-lists")
    store.save(LILY, "dup", [WORDS[0], WORDS[0], WORDS[2]])
    path = store.folder(LILY) / "dup.md"
    store.remove_word(LILY, path, "zealous", "热心的")
    assert [i.english for i in load_vocabulary(path.parent)[0]] == ["zealous", "tyre"]


def test_missing_word_raises_and_changes_nothing(setup):
    store, path = setup
    digest = sha(path)
    with pytest.raises(KeyError):
        store.remove_word(LILY, path, "absent", "无")
    assert sha(path) == digest


def test_paths_outside_own_folder_are_refused(setup, tmp_path):
    store, _ = setup
    shared = tmp_path / "vocab.md"
    shared.write_text("---\nenglish: river\nchinese: 河\n---\n", encoding="utf-8")
    store.save(WEIBO, "w", WORDS)
    other = store.folder(WEIBO) / "w.md"
    for target in (shared, other):
        digest = sha(target)
        with pytest.raises(ValueError):
            store.remove_word(LILY, target, "river", "河")
        with pytest.raises(ValueError):
            store.restore_word(LILY, RemovedEntry(target, 0, "x", target.read_text("utf-8")))
        assert sha(target) == digest


def test_hidden_shared_words(tmp_path):
    store = WordListStore(tmp_path / "word-lists")
    store.hide_shared(LILY, "t-words", "tablet", "药片")
    store.hide_shared(LILY, None, "lake", "湖")
    assert store.hidden_shared(LILY) == {("t-words", "tablet", "药片"), (None, "lake", "湖")}
    data = json.loads((store.folder(LILY) / ".hidden-shared.json").read_text("utf-8"))
    assert data["version"] == 1
    assert store.list(LILY) == []
    assert store.word_source(LILY) == "shared"
    assert store.hidden_shared(WEIBO) == set()
    store.unhide_shared(LILY, "t-words", "tablet", "药片")
    assert store.hidden_shared(LILY) == {(None, "lake", "湖")}


def test_unreadable_hidden_file_reads_empty(tmp_path):
    store = WordListStore(tmp_path / "word-lists")
    store.folder(LILY).mkdir(parents=True)
    (store.folder(LILY) / ".hidden-shared.json").write_text("{", encoding="utf-8")
    assert store.hidden_shared(LILY) == set()
