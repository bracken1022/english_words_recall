"""Tests for python -m src.tools.add_pos (spec 019,
contracts/add-pos-tool-contract.md)."""

import difflib
from pathlib import Path

import pytest

from src.services.vocabulary_loader import load_vocabulary
from src.tools import add_pos

WORDS = """---
english: rent
ipa: rent
alternates: []
chinese: 租金；租用；（动词）出租
group: ra
---

---
english: zealous
alternates:
- keen
chinese: 热心的
group: z
---

---
english: "tend to"
alternates: []
chinese: 倾向于
---

---
english: undertake
pos: [v.]
chinese: 承担
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
        "# file\tenglish\tpos\tnote\n"
        "vocab/words.md\trent\tn. v.\t租金 then 出租\n"
        "vocab/words.md\tzealous\tadjective\t\n"
        "vocab/words.md\ttend to\t\tphrase or verb pattern — unsure\n",
        encoding="utf-8",
    )
    return vocab / "words.md", mapping


def _run(mapping, *args):
    return add_pos.main(["--mapping", str(mapping), "--backup-root", "backups", *args])


def _added_lines(before: str, after: str) -> list[str]:
    diff = list(difflib.ndiff(before.splitlines(), after.splitlines()))
    assert not [line for line in diff if line.startswith("- ")]
    return [line[2:] for line in diff if line.startswith("+ ")]


def test_inserts_only_pos_lines_after_ipa_or_english(setup, capsys):
    words, mapping = setup
    assert _run(mapping, "vocab/words.md") == 0
    after = words.read_text(encoding="utf-8")
    assert _added_lines(WORDS, after) == ["pos: [n., v.]", "pos: [adj.]"]
    assert "english: rent\nipa: rent\npos: [n., v.]\nalternates:" in after
    assert "english: zealous\npos: [adj.]\nalternates:" in after
    out = capsys.readouterr().out
    assert "filled 2 · already had 1 · left empty 1 · missing from mapping 1" in out


def test_invalid_mapping_changes_nothing(setup, capsys):
    words, mapping = setup
    mapping.write_text("vocab/words.md\tzealous\tverbish\t\n", encoding="utf-8")
    assert _run(mapping, "vocab/words.md") == 1
    assert words.read_text(encoding="utf-8") == WORDS
    assert not Path("backups").exists()
    assert "vocab/words.md: zealous:" in capsys.readouterr().out


def test_dry_run_writes_nothing(setup, capsys):
    words, mapping = setup
    assert _run(mapping, "--dry-run", "vocab/words.md") == 0
    assert words.read_text(encoding="utf-8") == WORDS
    assert not Path("backups").exists()
    assert "filled 2" in capsys.readouterr().out


def test_backup_review_and_mapping_copy(setup):
    _, mapping = setup
    _run(mapping, "vocab/words.md")
    (run_dir,) = Path("backups").glob("pos-*")
    assert (run_dir / "files" / "vocab" / "words.md").read_text(encoding="utf-8") == WORDS
    assert (run_dir / "mapping.tsv").exists()
    review = (run_dir / "REVIEW.md").read_text(encoding="utf-8")
    assert "## Filled" in review
    assert "| vocab/words.md | rent | n. v. | 租金 then 出租 |" in review
    assert "## Left empty" in review
    assert "phrase or verb pattern — unsure" in review
    assert "## Missing from mapping" in review
    assert "## Spot check" in review
    spot = review.split("## Spot check", 1)[1]
    assert spot.count("| rent") + spot.count("| zealous") == 2


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
    monkeypatch.setattr(add_pos, "_snapshot", lambda path: ([str(path.stat().st_mtime_ns)], 0))
    assert _run(mapping, "vocab/words.md") == 1
    assert words.read_text(encoding="utf-8") == WORDS


def test_reloaded_vocabulary_unchanged_except_pos(setup):
    words, mapping = setup
    before, _ = load_vocabulary(words.parent)
    _run(mapping, "vocab/words.md")
    after, warnings = load_vocabulary(words.parent)
    assert warnings == []
    key = lambda i: (i.english, i.chinese, i.alternates, i.group, i.ipa)
    assert [key(i) for i in after] == [key(i) for i in before]
    assert [i.pos for i in after] == [["n.", "v."], ["adj."], [], ["v."], []]
