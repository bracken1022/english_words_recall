"""Tests for saving and preparing example sentences (spec 021, research
R5/R6): own lists keep the example in the word's block; other words use a
hidden .examples.json beside their file."""

import hashlib
import json
import threading
from pathlib import Path

import pytest

from src.models.account import Account
from src.models.vocabulary_item import VocabularyItem
from src.services.example_client import ExampleReply
from src.services.examples import ExampleService, ExampleUnavailable
from src.services.vocabulary_loader import load_vocabulary
from src.services.word_lists import WordListStore

LILY = Account("lily", "pw", "Lily", Path("p.md"))
GOOD = ExampleReply("ok", "She is a zealous supporter of the team.", "她是球队的狂热支持者。")
OTHER = ExampleReply("ok", "He was zealous about saving energy.", "他热衷于节约能源。")
WORDS = [
    VocabularyItem("zealous", "热心的", pos=["adj."]),
    VocabularyItem("rent", "租金", pos=["n."]),
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def own(tmp_path):
    store = WordListStore(tmp_path / "word-lists")
    store.save(LILY, "unit1", WORDS)
    path = store.folder(LILY) / "unit1.md"
    items, _ = load_vocabulary(path.parent)
    return store, path, items


@pytest.fixture
def shared(tmp_path):
    folder = tmp_path / "vocab"
    folder.mkdir()
    (folder / "t.md").write_text(
        "---\nenglish: zealous\nchinese: 热心的\ngroup: z\n---\n", encoding="utf-8"
    )
    items, _ = load_vocabulary(folder)
    return folder, items


class Gen:
    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = 0
        self.avoided = []

    def __call__(self, english, chinese, pos, base_url, model, avoid=None):
        self.calls += 1
        self.avoided.append(avoid)
        return self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]


def test_set_example_edits_only_that_block(own):
    store, path, _ = own
    before = path.read_text(encoding="utf-8")
    store.set_example(LILY, path, "zealous", "热心的", "It said: #1 fan.", "它说：头号粉丝。")
    after = path.read_text(encoding="utf-8")
    rent_block = before[before.index("---\nenglish: rent") :]
    assert after.endswith(rent_block)
    items, warnings = load_vocabulary(path.parent)
    assert warnings == []
    assert (items[0].example, items[0].example_zh) == ("It said: #1 fan.", "它说：头号粉丝。")
    assert items[1].example is None
    store.set_example(LILY, path, "zealous", "热心的", "New one here.", "新的。")
    items, _ = load_vocabulary(path.parent)
    assert items[0].example == "New one here."
    assert path.read_text(encoding="utf-8").count("example:") == 1


def test_own_list_example_saved_in_block(own):
    store, path, items = own
    service = ExampleService(store, "u", "m", generate=Gen(GOOD)).bind(LILY)
    service.prepare(items[0])
    service.wait(items[0], 5)
    assert service.status(items[0]) == "ready"
    assert service.get(items[0]) == {"sentence": GOOD.sentence, "translation": GOOD.translation}
    reloaded, _ = load_vocabulary(path.parent)
    assert reloaded[0].example == GOOD.sentence


def test_shared_example_saved_in_json(shared):
    folder, items = shared
    before = sha(folder / "t.md")
    service = ExampleService(None, "u", "m", generate=Gen(GOOD)).bind(None)
    service.prepare(items[0])
    service.wait(items[0], 5)
    assert sha(folder / "t.md") == before
    data = json.loads((folder / ".examples.json").read_text(encoding="utf-8"))
    assert data["version"] == 1
    assert data["examples"]["z|zealous|热心的"]["sentence"] == GOOD.sentence
    fresh = ExampleService(None, "u", "m", generate=Gen(OTHER)).bind(None)
    assert fresh.get(items[0])["sentence"] == GOOD.sentence


def test_block_example_preferred(shared):
    _, items = shared
    item = items[0]
    item.example, item.example_zh = "From the block.", "来自词条。"
    service = ExampleService(None, "u", "m", generate=Gen(GOOD)).bind(None)
    assert service.get(item)["sentence"] == "From the block."


def test_prepare_runs_once(shared):
    _, items = shared
    gate = threading.Event()

    def slow(*_args):
        gate.wait(5)
        return GOOD

    gen = Gen(GOOD)
    service = ExampleService(None, "u", "m", generate=lambda *a: (gen(*a), slow())[1]).bind(None)
    service.prepare(items[0])
    service.prepare(items[0])
    assert service.status(items[0]) == "pending"
    gate.set()
    service.wait(items[0], 5)
    assert gen.calls == 1
    assert service.status(items[0]) == "ready"


def test_unavailable_and_retry_once(shared):
    folder, items = shared
    down = ExampleService(None, "u", "m", generate=Gen(ExampleReply("unavailable"))).bind(None)
    down.prepare(items[0])
    down.wait(items[0], 5)
    assert down.status(items[0]) == "unavailable"

    bad = ExampleReply("ok", "No target word here at all.", "这里没有。")
    gen = Gen(bad, GOOD)
    retry = ExampleService(None, "u", "m", generate=gen).bind(None)
    retry.prepare(items[0])
    retry.wait(items[0], 5)
    assert gen.calls == 2
    assert retry.status(items[0]) == "ready"

    (folder / ".examples.json").unlink()  # forget the example just saved
    gen2 = Gen(bad)
    never = ExampleService(None, "u", "m", generate=gen2).bind(None)
    never.prepare(items[0])
    never.wait(items[0], 5)
    assert gen2.calls == 2
    assert never.status(items[0]) == "unavailable"


def test_renew(own):
    store, path, items = own
    service = ExampleService(store, "u", "m", generate=Gen(GOOD, OTHER)).bind(LILY)
    service.prepare(items[0])
    service.wait(items[0], 5)
    assert service.renew(items[0])["sentence"] == OTHER.sentence
    assert load_vocabulary(path.parent)[0][0].example == OTHER.sentence

    down = ExampleService(store, "u", "m", generate=Gen(ExampleReply("unavailable"))).bind(LILY)
    with pytest.raises(ExampleUnavailable):
        down.renew(items[0])
    assert load_vocabulary(path.parent)[0][0].example == OTHER.sentence


def test_removing_word_removes_its_example(own):
    store, path, _ = own
    store.set_example(LILY, path, "zealous", "热心的", GOOD.sentence, GOOD.translation)
    store.remove_word(LILY, path, "zealous", "热心的")
    assert "example" not in path.read_text(encoding="utf-8")


def test_renew_never_repeats_the_old_sentence(own):
    # Quickstart scenario d: the model may answer a renewal with the same
    # sentence; that counts as invalid and is retried once.
    store, path, items = own
    gen = Gen(GOOD, GOOD, OTHER)
    service = ExampleService(store, "u", "m", generate=gen).bind(LILY)
    service.prepare(items[0])
    service.wait(items[0], 5)
    assert service.renew(items[0])["sentence"] == OTHER.sentence
    assert gen.avoided == [None, GOOD.sentence, GOOD.sentence]

    service.service.generate = Gen(OTHER)  # only ever repeats the current one
    with pytest.raises(ExampleUnavailable):
        service.renew(items[0])
    assert load_vocabulary(path.parent)[0][0].example == OTHER.sentence
