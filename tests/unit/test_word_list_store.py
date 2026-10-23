"""Unit tests for sanitize_list_name and WordListStore (spec 016,
data-model.md "Word List")."""

from pathlib import Path

import pytest

from src.models.account import Account
from src.models.vocabulary_item import VocabularyItem
from src.services.vocabulary_loader import load_vocabulary
from src.services.word_lists import ListExistsError, WordListStore, sanitize_list_name

LILY = Account("lily", "pw", None, Path("progress-lily.md"))
WEIBO = Account("weibo", "pw", None, Path("progress.md"))


def _items(*words: str) -> list[VocabularyItem]:
    return [VocabularyItem(english=w, chinese=f"{w}-中") for w in words]


@pytest.mark.parametrize(
    ("stem", "expected"),
    [
        ("Unit 1", "Unit 1"),
        ("  my   words ", "my words"),
        ("../../etc/passwd", "etcpasswd"),
        (".hidden", "hidden"),
        ("单元一", "单元一"),
        ("T_words-2", "T_words-2"),
        ("$$$", ""),
    ],
)
def test_sanitize_list_name(stem, expected):
    assert sanitize_list_name(stem) == expected


def test_sanitize_truncates_to_64():
    assert len(sanitize_list_name("a" * 80)) == 64


def test_save_writes_loadable_markdown_with_group_set_to_name(tmp_path: Path):
    store = WordListStore(tmp_path)
    items = [
        VocabularyItem(english="receive", chinese="收到", alternates=["accept"], group="x"),
        VocabularyItem(english="on", chinese="在上面"),
    ]
    result = store.save(LILY, "unit1", items)
    assert result.name == "unit1"
    assert result.replaced is False
    assert result.first_list is True

    loaded, warnings = load_vocabulary(tmp_path / "lily")
    assert warnings == []
    assert [(i.english, i.chinese, i.alternates, i.group) for i in loaded] == [
        ("receive", "收到", ["accept"], "unit1"),
        ("on", "在上面", [], "unit1"),
    ]


def test_second_save_is_not_first_list(tmp_path: Path):
    store = WordListStore(tmp_path)
    store.save(LILY, "a", _items("x"))
    assert store.save(LILY, "b", _items("y")).first_list is False


def test_empty_name_becomes_my_words_then_numbered(tmp_path: Path):
    store = WordListStore(tmp_path)
    assert store.save(LILY, "", _items("x")).name == "My words"
    assert store.save(LILY, "", _items("y")).name == "My words 2"


def test_existing_name_case_insensitive_requires_replace(tmp_path: Path):
    store = WordListStore(tmp_path)
    store.save(LILY, "unit1", _items("old"))
    before = (tmp_path / "lily" / "unit1.md").read_text(encoding="utf-8")
    with pytest.raises(ListExistsError) as exc:
        store.save(LILY, "Unit1", _items("new"))
    assert exc.value.name == "unit1"
    assert (tmp_path / "lily" / "unit1.md").read_text(encoding="utf-8") == before


def test_replace_overwrites_same_file(tmp_path: Path):
    store = WordListStore(tmp_path)
    store.save(LILY, "unit1", _items("old"))
    result = store.save(LILY, "Unit1", _items("new"), replace=True)
    assert result.replaced is True
    assert result.name == "unit1"
    assert sorted(p.name for p in (tmp_path / "lily").iterdir()) == ["unit1.md"]
    loaded, _ = load_vocabulary(tmp_path / "lily")
    assert [i.english for i in loaded] == ["new"]


def test_no_temp_files_left(tmp_path: Path):
    store = WordListStore(tmp_path)
    store.save(LILY, "unit1", _items("x"))
    assert [p.suffix for p in (tmp_path / "lily").iterdir()] == [".md"]


def test_effective_dir_and_word_source(tmp_path: Path):
    shared = tmp_path / "shared"
    store = WordListStore(tmp_path / "lists")
    assert store.effective_dir(LILY, shared) == shared
    assert store.word_source(LILY) == "shared"
    store.save(LILY, "unit1", _items("x"))
    assert store.effective_dir(LILY, shared) == tmp_path / "lists" / "lily"
    assert store.word_source(LILY) == "own"
    assert store.effective_dir(WEIBO, shared) == shared


def test_accounts_are_isolated(tmp_path: Path):
    store = WordListStore(tmp_path)
    store.save(LILY, "unit1", _items("x"))
    assert not (tmp_path / "weibo").exists()


# --- US3: list and delete ------------------------------------------------------


def test_list_returns_sorted_names_counts_and_dates(tmp_path: Path):
    store = WordListStore(tmp_path)
    store.save(LILY, "B", _items("x", "y"))
    store.save(LILY, "a", _items("z"))
    lists = store.list(LILY)
    assert [(entry["name"], entry["word_count"]) for entry in lists] == [("a", 1), ("B", 2)]
    for entry in lists:
        assert entry["uploaded_at"].endswith("+00:00")
    assert store.list(WEIBO) == []


def test_delete_is_case_insensitive_and_falls_back_to_shared(tmp_path: Path):
    store = WordListStore(tmp_path / "lists")
    store.save(LILY, "unit1", _items("x"))
    assert store.delete(LILY, "UNIT1") == "unit1"
    assert store.list(LILY) == []
    assert store.effective_dir(LILY, tmp_path / "shared") == tmp_path / "shared"


def test_delete_unknown_raises_keyerror(tmp_path: Path):
    with pytest.raises(KeyError):
        WordListStore(tmp_path).delete(LILY, "nope")


def test_delete_cannot_reach_another_account(tmp_path: Path):
    store = WordListStore(tmp_path)
    store.save(WEIBO, "unit1", _items("x"))
    store.save(LILY, "mine", _items("y"))
    with pytest.raises(KeyError):
        store.delete(LILY, "../weibo/unit1")
    assert (tmp_path / "weibo" / "unit1.md").exists()


def test_saved_list_keeps_ipa_after_english(tmp_path: Path):
    store = WordListStore(tmp_path)
    items = [
        VocabularyItem(english="receive", chinese="收到", ipa="rɪˈsiːv"),
        VocabularyItem(english="plain", chinese="普通"),
    ]
    store.save(LILY, "unit1", items)
    text = (tmp_path / "lily" / "unit1.md").read_text(encoding="utf-8")
    assert "english: receive\nipa: rɪˈsiːv\n" in text
    assert text.count("ipa:") == 1
    loaded, _ = load_vocabulary(tmp_path / "lily")
    assert [i.ipa for i in loaded] == ["rɪˈsiːv", None]


# --- spec 019: pos is saved in key order, as a one-line list -----------------


def test_pos_round_trips_in_key_order(tmp_path):
    from src.lib.markdown_blocks import parse_blocks
    from src.models.account import Account
    from src.models.vocabulary_item import VocabularyItem
    from src.services.word_lists import WordListStore

    lily = Account("lily", "pw", "Lily", tmp_path / "p.md")
    store = WordListStore(tmp_path)
    item = VocabularyItem("rent", "租金；出租", ipa="rent", pos=["n.", "v."])
    store.save(lily, "unit1", [item])
    text = (tmp_path / "lily" / "unit1.md").read_text(encoding="utf-8")
    assert "pos: [n., v.]\n" in text
    (block,), _ = parse_blocks(text)
    assert list(block) == ["english", "ipa", "pos", "alternates", "chinese", "group"]
    assert VocabularyItem.from_block(block).pos == ["n.", "v."]


# --- spec 023: set_values corrects ipa, chinese and pos in one block ---------

_LIST = (
    "---\nenglish: tailor\nipa: ˈteɪlə\npos: [v.]\nalternates: [taylor]\nchinese: 裁缝\n"
    "group: unit1\nexample: 'The tailor said: no #1.'\nexample_zh: 裁缝说不。\n---\n\n"
    "---\nenglish: plain\nalternates: []\nchinese: 普通\ngroup: unit1\n---\n"
)


def _values(ipa, chinese, pos):
    from src.services.corrections_file import WordValues

    return WordValues.normal(ipa, chinese, pos)


def _list_file(tmp_path: Path) -> Path:
    path = tmp_path / "lily" / "unit1.md"
    path.parent.mkdir(parents=True)
    path.write_text(_LIST, encoding="utf-8")
    return path


def test_set_values_changes_only_the_three_fields(tmp_path: Path):
    store = WordListStore(tmp_path)
    path = _list_file(tmp_path)
    old = _values("ˈteɪlə", "裁缝", ["v."])
    new = _values("ˈteɪlə", "裁缝；定做: 衣服 #2", ["n.", "v."])
    assert store.set_values(LILY, path, "tailor", old, new) is True
    text = path.read_text(encoding="utf-8")
    assert text == _LIST.replace("pos: [v.]", "pos: [n., v.]").replace(
        "chinese: 裁缝\n", "chinese: '裁缝；定做: 衣服 #2'\n"
    )
    items, warnings = load_vocabulary(path.parent)
    assert warnings == []
    assert (items[0].chinese, items[0].pos, items[0].alternates) == (
        "裁缝；定做: 衣服 #2",
        ["n.", "v."],
        ["taylor"],
    )
    assert items[0].example == "The tailor said: no #1."


def test_set_values_adds_missing_ipa_and_pos_after_english(tmp_path: Path):
    store = WordListStore(tmp_path)
    path = _list_file(tmp_path)
    old = _values(None, "普通", [])
    new = _values("pleɪn", "普通的；平原", ["adj.", "n."])
    assert store.set_values(LILY, path, "plain", old, new) is True
    text = path.read_text(encoding="utf-8")
    assert (
        "english: plain\nipa: pleɪn\npos: [adj., n.]\nalternates: []\nchinese: 普通的；平原\n"
        in text
    )
    assert text.startswith(_LIST.split("\n\n")[0])


def test_set_values_refuses_when_the_block_changed(tmp_path: Path):
    store = WordListStore(tmp_path)
    path = _list_file(tmp_path)
    stale = _values("ˈteɪlə", "裁缝；旧的", ["v."])
    assert store.set_values(LILY, path, "tailor", stale, _values("ˈteɪlə", "x", ["n."])) is False
    assert store.set_values(LILY, path, "gone", stale, _values("ˈteɪlə", "x", ["n."])) is False
    assert path.read_text(encoding="utf-8") == _LIST


def test_set_values_stays_in_the_accounts_folder(tmp_path: Path):
    store = WordListStore(tmp_path)
    other = tmp_path / "weibo" / "unit1.md"
    other.parent.mkdir(parents=True)
    other.write_text(_LIST, encoding="utf-8")
    with pytest.raises(ValueError):
        store.set_values(
            LILY, other, "tailor", _values("ˈteɪlə", "裁缝", ["v."]), _values(None, "x", ["n."])
        )


def test_word_values_lists_every_block_of_a_word(tmp_path: Path):
    store = WordListStore(tmp_path)
    path = _list_file(tmp_path)
    assert store.word_values(LILY, path, "tailor") == [_values("ˈteɪlə", "裁缝", ["v."])]
    assert store.word_values(LILY, path, "gone") == []
