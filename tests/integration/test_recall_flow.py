
from src.cli.session import run_recall_step
from src.models.vocabulary_item import VocabularyItem


def test_recall_step_hides_english_until_submitted(capsys):
    item = VocabularyItem(english="receive", chinese="收到")
    run_recall_step(item, answer_input=lambda: "receive")
    out = capsys.readouterr().out
    assert "收到" in out
    # The English expression must not appear on the line showing the meaning.
    meaning_line = out.splitlines()[0]
    assert "receive" not in meaning_line.lower()


def test_correct_answer_marks_correct_and_reveals(capsys):
    item = VocabularyItem(english="receive", chinese="收到")
    attempt = run_recall_step(item, answer_input=lambda: "receive")
    out = capsys.readouterr().out
    assert attempt.correct is True
    assert "correct" in out.lower()
    assert "receive" in out.lower()


def test_incorrect_answer_marks_incorrect_and_reveals(capsys):
    item = VocabularyItem(english="receive", chinese="收到")
    attempt = run_recall_step(item, answer_input=lambda: "wrong")
    out = capsys.readouterr().out
    assert attempt.correct is False
    assert "receive" in out.lower()


def test_empty_answer_is_incorrect_without_error(capsys):
    item = VocabularyItem(english="receive", chinese="收到")
    attempt = run_recall_step(item, answer_input=lambda: "")
    assert attempt.correct is False
    assert attempt.answer == ""
