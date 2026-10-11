from pathlib import Path
from unittest.mock import patch

from src.cli.session import run_session
from tests.fake_examples import FakeExampleService

# answer, then Enter to continue, for each word (spec 021 example mode)
ANSWERS = ["receive", "", "give up", ""]


def _write_two_item_vocab(tmp_path: Path) -> Path:
    vocab_dir = tmp_path / "vocab"
    vocab_dir.mkdir()
    (vocab_dir / "all.md").write_text(
        "---\nenglish: receive\nchinese: 收到\n---\n\n---\nenglish: give up\nchinese: 放弃\n---\n"
    )
    return vocab_dir


@patch("src.cli.session.random.shuffle")
@patch("src.cli.session.ExampleService", FakeExampleService)
def test_random_order_shuffles_the_filtered_pool(mock_shuffle, tmp_path: Path, monkeypatch):
    vocab_dir = _write_two_item_vocab(tmp_path)
    answers = iter(ANSWERS)
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))

    run_session(vocab_dir=vocab_dir, progress_file=tmp_path / "p.md", order="random")

    mock_shuffle.assert_called_once()


@patch("src.cli.session.random.shuffle")
@patch("src.cli.session.ExampleService", FakeExampleService)
def test_sequential_order_never_shuffles(mock_shuffle, tmp_path: Path, monkeypatch):
    vocab_dir = _write_two_item_vocab(tmp_path)
    answers = iter(ANSWERS)
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))

    run_session(vocab_dir=vocab_dir, progress_file=tmp_path / "p.md", order="sequential")

    mock_shuffle.assert_not_called()


@patch("src.cli.session.random.shuffle")
@patch("src.cli.session.ExampleService", FakeExampleService)
def test_default_order_never_shuffles(mock_shuffle, tmp_path: Path, monkeypatch):
    vocab_dir = _write_two_item_vocab(tmp_path)
    answers = iter(ANSWERS)
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))

    run_session(vocab_dir=vocab_dir, progress_file=tmp_path / "p.md")

    mock_shuffle.assert_not_called()


@patch("src.cli.session.ExampleService", FakeExampleService)
def test_random_order_still_presents_every_word_exactly_once(tmp_path: Path, monkeypatch):
    vocab_dir = _write_two_item_vocab(tmp_path)
    progress_file = tmp_path / "progress.md"
    answers = iter(ANSWERS)
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))

    run_session(vocab_dir=vocab_dir, progress_file=progress_file, order="random")

    text = progress_file.read_text(encoding="utf-8")
    assert text.count("item: receive") == 1
    assert text.count("item: give up") == 1
