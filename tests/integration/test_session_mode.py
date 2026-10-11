from pathlib import Path
from unittest.mock import patch

from src.cli.session import run_session
from tests.fake_examples import FakeExampleService


def _write_two_item_vocab(tmp_path: Path) -> Path:
    vocab_dir = tmp_path / "vocab"
    vocab_dir.mkdir()
    (vocab_dir / "all.md").write_text(
        "---\nenglish: receive\nchinese: 收到\n---\n\n---\nenglish: give up\nchinese: 放弃\n---\n"
    )
    return vocab_dir


def test_recall_only_mode_never_asks_for_examples(tmp_path: Path, monkeypatch):
    service = FakeExampleService()
    vocab_dir = _write_two_item_vocab(tmp_path)
    answers = iter(["receive", "give up"])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))

    with patch("src.cli.session.ExampleService", lambda *a, **k: service):
        run_session(vocab_dir=vocab_dir, progress_file=tmp_path / "p.md", mode="recall-only")

    assert service.asked == []


def test_recall_only_mode_records_every_word_without_sentence_or_feedback(
    tmp_path: Path, monkeypatch
):
    vocab_dir = _write_two_item_vocab(tmp_path)
    progress_file = tmp_path / "progress.md"
    answers = iter(["receive", "give up"])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))

    run_session(vocab_dir=vocab_dir, progress_file=progress_file, mode="recall-only")

    text = progress_file.read_text(encoding="utf-8")
    assert "item: receive" in text
    assert "item: give up" in text
    assert "sentence:" not in text
    assert "feedback:" not in text


def test_example_mode_default_shows_an_example_per_word(tmp_path: Path, monkeypatch, capsys):
    service = FakeExampleService()
    vocab_dir = _write_two_item_vocab(tmp_path)
    progress_file = tmp_path / "progress.md"
    # answer, then Enter to continue, for each word
    answers = iter(["receive", "", "give up", ""])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))

    with patch("src.cli.session.ExampleService", lambda *a, **k: service):
        run_session(vocab_dir=vocab_dir, progress_file=progress_file)

    assert service.asked == ["receive", "give up"]
    out = capsys.readouterr().out
    assert out.count("Example: I received a gift from my aunt.") == 2
    text = progress_file.read_text(encoding="utf-8")
    assert "answer: receive" in text
    assert "answer: give up" in text


def test_sentence_mode_means_example_mode(tmp_path: Path, monkeypatch):
    service = FakeExampleService()
    vocab_dir = _write_two_item_vocab(tmp_path)
    answers = iter(["receive", "", "give up", ""])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))

    with patch("src.cli.session.ExampleService", lambda *a, **k: service):
        run_session(vocab_dir=vocab_dir, progress_file=tmp_path / "p.md", mode="sentence")

    assert service.asked == ["receive", "give up"]


def test_no_example_available_still_completes(tmp_path: Path, monkeypatch, capsys):
    vocab_dir = _write_two_item_vocab(tmp_path)
    progress_file = tmp_path / "progress.md"
    answers = iter(["receive", "", "give up", ""])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))

    with patch("src.cli.session.ExampleService", lambda *a, **k: FakeExampleService(example=None)):
        run_session(vocab_dir=vocab_dir, progress_file=progress_file)

    assert "(No example right now.)" in capsys.readouterr().out
    assert "item: give up" in progress_file.read_text(encoding="utf-8")


def test_recall_only_wrong_answer_waits_for_an_extra_confirmation(tmp_path: Path, monkeypatch):
    """Spec 013: a wrong recall-only answer must block on one extra
    input() call (the "press Enter to continue" pause) before the
    session moves on to the next word."""
    vocab_dir = _write_two_item_vocab(tmp_path)
    progress_file = tmp_path / "progress.md"
    # "wrong" (incorrect answer), "" (the confirmation pause), "give up" (correct, no pause needed)
    answers = iter(["wrong", "", "give up"])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))

    run_session(vocab_dir=vocab_dir, progress_file=progress_file, mode="recall-only")

    text = progress_file.read_text(encoding="utf-8")
    assert "item: receive" in text
    assert "answer: wrong" in text
    assert "correct: false" in text
    assert "item: give up" in text
    # Only if the confirmation pause actually consumed the blank input()
    # value did "give up" (not "") land as the second item's real answer.
    assert "answer: give up" in text


def test_recall_only_correct_answer_needs_no_extra_confirmation(tmp_path: Path, monkeypatch):
    """Regression guard: a correct recall-only answer must NOT consume an
    extra input() value — only one scripted answer per word is needed."""
    vocab_dir = _write_two_item_vocab(tmp_path)
    progress_file = tmp_path / "progress.md"
    answers = iter(["receive", "give up"])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))

    run_session(vocab_dir=vocab_dir, progress_file=progress_file, mode="recall-only")

    text = progress_file.read_text(encoding="utf-8")
    assert "item: receive" in text
    assert "item: give up" in text
