"""Assertions for the dev-time design/ folder and its runtime boundary
(spec 014, contracts/reference-folder-contract.md): references live in a
predictable place, and nothing the app ships ever depends on them."""

from pathlib import Path

import pytest

from src.services.vocabulary_loader import load_vocabulary
from src.web.app import create_app

REPO_ROOT = Path(__file__).resolve().parents[2]
DESIGN_DIR = REPO_ROOT / "design"
REFERENCE_FOLDERS = ("vocabulary-practice", "sentence-practice", "progress", "shared")
SRC_DIR = REPO_ROOT / "src"


# --- User Story 1: predictable reference location ---


@pytest.mark.parametrize("folder", REFERENCE_FOLDERS)
def test_reference_folder_exists_and_is_tracked(folder):
    assert (DESIGN_DIR / "references" / folder / ".gitkeep").is_file()


def test_design_readme_explains_folders_and_boundaries():
    text = (DESIGN_DIR / "README.md").read_text(encoding="utf-8")
    for needle in (*REFERENCE_FOLDERS, "notes.md", "png", "jpg", "runtime", "logo"):
        assert needle in text, f"design/README.md missing '{needle}'"


# --- User Story 2: references are never a runtime dependency ---


def test_no_application_source_refers_to_design_folder():
    for path in SRC_DIR.rglob("*"):
        if path.suffix in {".py", ".html", ".css", ".js"}:
            assert "design/" not in path.read_text(encoding="utf-8"), path


def test_app_serves_pages_without_design_folder(tmp_path, monkeypatch):
    vocab_dir = tmp_path / "vocab"
    vocab_dir.mkdir()
    (vocab_dir / "words.md").write_text(
        "---\nenglish: river\nalternates: []\nchinese: 河\ngroup: g\n---\n", encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    assert not (tmp_path / "design").exists()

    client = create_app(vocab_dir=vocab_dir, progress_file=tmp_path / "progress.md").test_client()
    assert client.get("/").status_code == 200
    assert client.get("/static/style.css").status_code == 200


# --- User Story 3: isolated verification inputs ---


def test_verification_screenshots_are_git_ignored():
    lines = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "/design/verification/" in lines


def test_fixture_vocabulary_loads_cleanly():
    items, warnings = load_vocabulary(DESIGN_DIR / "fixtures/vocabulary")
    assert warnings == []
    assert 3 <= len(items) <= 5
    assert all(item.group == "design-fixture" for item in items)
    assert any(item.alternates for item in items)
