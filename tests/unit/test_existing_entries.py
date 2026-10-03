"""Unit tests for existing-entry detection (spec 018 research R7): an
uploaded word is matched against the account's current vocabulary — its
own lists, or the shared folder while it has none."""

from pathlib import Path

from src.models.account import Account
from src.services.enrichment import PendingImportStore, existing_lookup_for
from src.services.word_lists import WordListStore

LILY = Account("lily", "pw", "Lily", Path("p.md"))


def _setup(tmp_path):
    shared = tmp_path / "vocab"
    shared.mkdir()
    (shared / "t.md").write_text(
        "---\nenglish: river\nchinese: 河\ngroup: t-words\n---\n\n"
        "---\nenglish: lake\nchinese: 湖\n---\n",
        encoding="utf-8",
    )
    return WordListStore(tmp_path / "word-lists"), shared


def test_matches_own_lists(tmp_path):
    store, shared = _setup(tmp_path)
    folder = store.folder(LILY)
    folder.mkdir(parents=True)
    (folder / "unit1.md").write_text(
        "---\nenglish: receive\nipa: rɪˈsiːv\nalternates: [accept]\nchinese: 收到\ngroup: unit1\n---\n",
        encoding="utf-8",
    )
    lookup = existing_lookup_for(store, LILY, shared)
    assert lookup("Receive ") == {
        "source": "own",
        "list": "unit1",
        "ipa": "rɪˈsiːv",
        "chinese": "收到",
        "alternates": ["accept"],
    }
    assert lookup("river") is None
    assert lookup("zealous") is None


def test_matches_shared_folder_without_own_lists(tmp_path):
    store, shared = _setup(tmp_path)
    lookup = existing_lookup_for(store, LILY, shared)
    assert lookup("river") == {
        "source": "shared",
        "list": "t-words",
        "ipa": None,
        "chinese": "河",
        "alternates": [],
    }
    assert lookup("lake")["list"] == "t"


def test_pending_file_is_never_a_list(tmp_path):
    store, shared = _setup(tmp_path)
    PendingImportStore(tmp_path / "word-lists").path(LILY).parent.mkdir(parents=True)
    (store.folder(LILY) / ".pending-import.json").write_text("{}", encoding="utf-8")
    lookup = existing_lookup_for(store, LILY, shared)
    assert lookup("river")["source"] == "shared"


def test_first_occurrence_wins(tmp_path):
    store, shared = _setup(tmp_path)
    folder = store.folder(LILY)
    folder.mkdir(parents=True)
    (folder / "a.md").write_text("---\nenglish: go\nchinese: 去\n---\n", encoding="utf-8")
    (folder / "b.md").write_text("---\nenglish: go\nchinese: 走\n---\n", encoding="utf-8")
    assert existing_lookup_for(store, LILY, shared)("go")["list"] == "a"
