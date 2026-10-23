"""Shared corrections applied on top of the shared files, and the file
meaning (origin_chinese) as a shared word's identity (spec 023, research
R4/R5)."""

import hashlib
import json
from pathlib import Path

import pytest

from src.models.account import Account
from src.models.vocabulary_item import VocabularyItem
from src.services import corrections_file as cf
from src.services.examples import ExampleService
from src.services.vocabulary_loader import load_vocabulary
from src.services.word_lists import WordListStore
from src.web.app import create_app
from src.web.session_registry import SessionRegistry

SHARED = (
    "---\nenglish: tailor\nchinese: 裁缝；定制\nipa: ˈteɪlə\npos: [n., v.]\ngroup: t-words\n"
    "alternates: [taylor]\nexample: The tailor made my suit.\nexample_zh: 裁缝做了我的西装。\n---\n\n"
    "---\nenglish: tidy\nchinese: 整洁的\nipa: ˈtaɪdi\npos: [adj.]\ngroup: t-words\n---\n"
)
FIXED = cf.WordValues.normal("ˈteɪlə", "裁缝；定做（衣服）", ["n.", "v."])
TAILOR_KEY = cf.overlay_key("T_words.md", "t-words", "tailor", "裁缝；定制")
LILY = Account("lily", "pw", "Lily", Path("pl.md"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def vocab(tmp_path):
    folder = tmp_path / "vocab"
    folder.mkdir()
    (folder / "T_words.md").write_text(SHARED, encoding="utf-8")
    return folder


def _overlay(folder: Path, key: str = TAILOR_KEY, values: cf.WordValues = FIXED) -> None:
    def fn(data):
        data.overlay[key] = values

    cf.update(folder, fn)


def _by_english(items):
    return {i.english: i for i in items}


def test_origin_chinese_is_the_file_meaning(vocab):
    items, _ = load_vocabulary(vocab)
    assert all(i.origin_chinese == i.chinese for i in items)
    assert VocabularyItem("a", "甲").origin_chinese == "甲"


def test_origin_chinese_is_not_compared():
    a = VocabularyItem("tailor", "裁缝")
    b = VocabularyItem("tailor", "裁缝")
    b.origin_chinese = "旧的"
    assert a == b


def test_overlay_replaces_the_three_fields_only(vocab):
    before = sha(vocab / "T_words.md")
    _overlay(vocab)
    items, warnings = load_vocabulary(vocab)
    tailor = _by_english(items)["tailor"]
    assert (tailor.ipa, tailor.chinese, tailor.pos) == (
        "ˈteɪlə",
        "裁缝；定做（衣服）",
        ["n.", "v."],
    )
    assert tailor.origin_chinese == "裁缝；定制"
    assert tailor.alternates == ["taylor"]
    assert tailor.group == "t-words"
    assert tailor.example == "The tailor made my suit."
    assert tailor.example_zh == "裁缝做了我的西装。"
    assert _by_english(items)["tidy"].chinese == "整洁的"
    assert warnings == []
    assert sha(vocab / "T_words.md") == before


def test_unknown_overlay_keys_are_ignored(vocab):
    _overlay(vocab, key=cf.overlay_key("T_words.md", "t-words", "tailor", "别的意思"))
    tailor = _by_english(load_vocabulary(vocab)[0])["tailor"]
    assert tailor.chinese == "裁缝；定制"


def test_unreadable_corrections_file_is_ignored(vocab):
    (vocab / cf.FILE_NAME).write_text("{not json", encoding="utf-8")
    items, warnings = load_vocabulary(vocab)
    assert _by_english(items)["tailor"].chinese == "裁缝；定制"
    assert warnings == []


def test_hidden_shared_word_stays_hidden_after_its_meaning_is_corrected(tmp_path, vocab):
    store = WordListStore(tmp_path / "word-lists")
    store.hide_shared(LILY, "t-words", "tailor", "裁缝；定制")
    _overlay(vocab)
    registry = SessionRegistry(
        vocab_dir=vocab,
        group=None,
        offer_choice=True,
        order="sequential",
        mode="example",
        word_lists=store,
    )
    items, _ = load_vocabulary(vocab)
    visible = registry._item_filter(LILY)(items)
    assert [i.english for i in visible] == ["tidy"]


def test_remove_route_hides_by_the_file_meaning(tmp_path, vocab):
    _overlay(vocab)
    app = create_app(
        vocab_dir=vocab,
        progress_file=tmp_path / "p.md",
        offer_choice=True,
        accounts=[Account("lily", "pw", "Lily", tmp_path / "pl.md")],
        word_lists_dir=tmp_path / "wl",
    )
    client = app.test_client()
    client.post("/api/login", json={"username": "lily", "password": "pw"})
    client.post("/api/select", json={"collection": "t-words", "mode": "recall-only"})
    assert client.get("/api/state").get_json()["chinese"] == "裁缝；定做（衣服）"
    assert client.post("/api/remove-word").status_code == 200
    hidden = json.loads((tmp_path / "wl" / "lily" / ".hidden-shared.json").read_text("utf-8"))
    assert hidden["hidden"] == [{"group": "t-words", "english": "tailor", "chinese": "裁缝；定制"}]


def test_shared_example_found_after_meaning_is_corrected(vocab):
    # A saved example for a word without inline example lines.
    (vocab / ".examples.json").write_text(
        json.dumps(
            {
                "version": 1,
                "examples": {
                    "t-words|tidy|整洁的": {
                        "sentence": "Keep it tidy.",
                        "translation": "保持整洁。",
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    _overlay(
        vocab,
        key=cf.overlay_key("T_words.md", "t-words", "tidy", "整洁的"),
        values=cf.WordValues.normal("ˈtaɪdi", "整洁的；整齐的", ["adj."]),
    )
    tidy = _by_english(load_vocabulary(vocab)[0])["tidy"]
    assert tidy.chinese == "整洁的；整齐的"
    service = ExampleService(None, "http://unused", "m")
    assert service.get(None, tidy) == {"sentence": "Keep it tidy.", "translation": "保持整洁。"}
