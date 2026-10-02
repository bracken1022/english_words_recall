"""Tests for python -m src.tools.add_ipa (spec 017,
contracts/add-ipa-tool-contract.md)."""

import difflib
from pathlib import Path

import pytest

from src.services.vocabulary_loader import load_vocabulary
from src.tools import add_ipa

WORDS = """---
english: dispute
alternates:
- argument
chinese: 争论；争端
group: dan
---

---
english: waist
alternates: []
chinese: 腰；腰部
group: w-words
---

---
english: "tend to"
alternates: []
chinese: 倾向于
group: t-words
---

---
english: tablet
ipa: ˈtæblət
chinese: 药片
---

---
english: unlisted
chinese: 未列出
---
"""


@pytest.fixture
def setup(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    vocab = tmp_path / "vocab"
    vocab.mkdir()
    (vocab / "words.md").write_text(WORDS, encoding="utf-8")
    mapping = tmp_path / "mapping.tsv"
    mapping.write_text(
        "# file\tenglish\tipa\tnote\n"
        "vocab/words.md\tdispute\tdɪˈspjuːt\tnoun and verb share stress\n"
        "vocab/words.md\twaist\tweɪst\t\n"
        "vocab/words.md\ttend to\t\tnot sure about the weak form\n",
        encoding="utf-8",
    )
    return vocab / "words.md", mapping


def _run(mapping, *args):
    return add_ipa.main(["--mapping", str(mapping), "--backup-root", "backups", *args])


def _added_lines(before: str, after: str) -> list[str]:
    diff = list(difflib.ndiff(before.splitlines(), after.splitlines()))
    assert not [line for line in diff if line.startswith("- ")]
    return [line[2:] for line in diff if line.startswith("+ ")]


def test_inserts_only_ipa_lines_after_english(setup, capsys):
    words, mapping = setup
    assert _run(mapping, "vocab/words.md") == 0
    after = words.read_text(encoding="utf-8")
    assert _added_lines(WORDS, after) == ["ipa: dɪˈspjuːt", "ipa: weɪst"]
    assert "english: dispute\nipa: dɪˈspjuːt\nalternates:" in after
    out = capsys.readouterr().out
    assert "filled 2 · already had 1 · left empty 1 · missing from mapping 1" in out


def test_validation_failure_changes_nothing(setup, capsys):
    words, mapping = setup
    mapping.write_text("vocab/words.md\twaist\tˈweɪstɚ\t\n", encoding="utf-8")
    assert _run(mapping, "vocab/words.md") == 1
    assert words.read_text(encoding="utf-8") == WORDS
    assert not Path("backups").exists()
    assert "vocab/words.md: waist:" in capsys.readouterr().out


def test_dry_run_writes_nothing(setup, capsys):
    words, mapping = setup
    assert _run(mapping, "--dry-run", "vocab/words.md") == 0
    assert words.read_text(encoding="utf-8") == WORDS
    assert not Path("backups").exists()
    assert "filled 2" in capsys.readouterr().out


def test_backup_review_and_mapping_copy(setup):
    _, mapping = setup
    _run(mapping, "vocab/words.md")
    (run_dir,) = Path("backups").glob("ipa-*")
    assert (run_dir / "files" / "vocab" / "words.md").read_text(encoding="utf-8") == WORDS
    assert (run_dir / "mapping.tsv").exists()
    review = (run_dir / "REVIEW.md").read_text(encoding="utf-8")
    assert "/dɪˈspjuːt/" in review
    assert "not sure about the weak form" in review
    assert "## Spot check" in review
    spot = review.split("## Spot check", 1)[1]
    assert spot.count("| dispute") + spot.count("| waist") == 2


def test_second_run_is_a_no_op(setup, capsys):
    words, mapping = setup
    _run(mapping, "vocab/words.md")
    after_first = words.read_text(encoding="utf-8")
    capsys.readouterr()
    assert _run(mapping, "vocab/words.md") == 0
    assert words.read_text(encoding="utf-8") == after_first
    assert "filled 0 · already had 3" in capsys.readouterr().out


def test_failed_verification_restores_original(setup, monkeypatch):
    words, mapping = setup
    monkeypatch.setattr(add_ipa, "_snapshot", lambda path: ([str(path.stat().st_mtime_ns)], 0))
    assert _run(mapping, "vocab/words.md") == 1
    assert words.read_text(encoding="utf-8") == WORDS


def test_reloaded_vocabulary_unchanged_except_ipa(setup):
    words, mapping = setup
    before, _ = load_vocabulary(words.parent)
    _run(mapping, "vocab/words.md")
    after, warnings = load_vocabulary(words.parent)
    assert warnings == []
    key = lambda i: (i.english, i.chinese, i.alternates, i.group)
    assert [key(i) for i in after] == [key(i) for i in before]
    assert [i.ipa for i in after] == ["dɪˈspjuːt", "weɪst", None, "ˈtæblət", None]
