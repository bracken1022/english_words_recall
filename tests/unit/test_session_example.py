"""PracticeSession with example sentences (spec 021, research R1): every
answer in an example mode goes to "reveal", which carries the word's
example; the attempt is logged once, at the end of the word."""

from pathlib import Path

import pytest

from src.services.examples import ExampleUnavailable
from src.web.session_state import PracticeSession, WrongStepError

VOCAB = (
    "---\nenglish: zealous\nchinese: 热心的\ngroup: unit1\n---\n\n"
    "---\nenglish: rent\nchinese: 租金\ngroup: unit1\n---\n"
)
EXAMPLE = {"sentence": "She is zealous about recycling.", "translation": "她热衷于回收利用。"}


class FakeExamples:
    def __init__(self, ready=True):
        self.ready = ready
        self.prepared = []
        self.renewed = []

    def prepare(self, item):
        self.prepared.append(item.english)

    def get(self, item):
        return dict(EXAMPLE) if self.ready else None

    def status(self, item):
        return "ready" if self.ready else "pending"

    def renew(self, item):
        if not self.ready:
            raise ExampleUnavailable(item.english)
        self.renewed.append(item.english)
        return {"sentence": "A new zealous sentence here.", "translation": "新的。"}


def _session(tmp_path: Path, examples=None, **kwargs) -> PracticeSession:
    vocab = tmp_path / "vocab"
    vocab.mkdir(exist_ok=True)
    (vocab / "unit1.md").write_text(VOCAB, encoding="utf-8")
    return PracticeSession(
        vocab_dir=vocab, progress_file=tmp_path / "progress.md", example_service=examples, **kwargs
    )


def _log(tmp_path) -> str:
    path = tmp_path / "progress.md"
    return path.read_text(encoding="utf-8") if path.exists() else ""


@pytest.mark.parametrize("mode", [None, "example", "sentence"])
def test_example_mode_reveals_every_answer(tmp_path, mode):
    kwargs = {} if mode is None else {"mode": mode}
    examples = FakeExamples()
    session = _session(tmp_path, examples, **kwargs)
    assert session.mode == "example"
    assert examples.prepared == ["zealous"]
    session.submit_answer("zealous")
    assert session.step == "reveal"
    assert _log(tmp_path) == ""
    state = session.state()
    assert state["correct"] is True
    assert state["example"] == EXAMPLE
    assert state["example_status"] == "ready"
    assert state["mode"] == "example"
    session.continue_to_next()
    assert _log(tmp_path).count("item: zealous") == 1
    assert session.step == "recall"
    assert examples.prepared == ["zealous", "rent"]


def test_wrong_answer_also_reveals(tmp_path):
    session = _session(tmp_path, FakeExamples())
    session.submit_answer("nope")
    assert session.step == "reveal"
    assert session.state()["correct"] is False


def test_pending_example(tmp_path):
    session = _session(tmp_path, FakeExamples(ready=False))
    session.submit_answer("zealous")
    state = session.state()
    assert (state["example"], state["example_status"]) == (None, "pending")


def test_recall_only_is_unchanged_and_never_prepares(tmp_path):
    examples = FakeExamples()
    session = _session(tmp_path, examples, mode="recall-only")
    session.submit_answer("zealous")
    assert session.step == "reveal"
    assert session.state()["example_status"] == "off"
    assert "example" not in session.state() or session.state()["example"] is None
    assert examples.prepared == []


def test_no_service_means_unavailable(tmp_path):
    session = _session(tmp_path, None)
    session.submit_answer("zealous")
    assert session.state()["example_status"] == "unavailable"


def test_renew_example(tmp_path):
    examples = FakeExamples()
    session = _session(tmp_path, examples)
    with pytest.raises(WrongStepError):
        session.renew_example()
    session.submit_answer("zealous")
    assert session.renew_example()["sentence"] == "A new zealous sentence here."
    assert examples.renewed == ["zealous"]


def test_renew_unavailable_propagates(tmp_path):
    session = _session(tmp_path, FakeExamples(ready=False))
    session.submit_answer("zealous")
    with pytest.raises(ExampleUnavailable):
        session.renew_example()


def test_select_collection_prepares_first_word(tmp_path):
    examples = FakeExamples()
    session = _session(tmp_path, examples, offer_choice=True)
    assert examples.prepared == []
    session.select_collection("unit1", mode="example")
    assert examples.prepared == ["zealous"]


# --- US2: self-checked sentence recall ------------------------------------------


def _at_sentence_recall(tmp_path, examples=None):
    session = _session(tmp_path, examples or FakeExamples(), mode="example-recall")
    session.submit_answer("zealous")
    session.continue_to_next()
    return session


def test_example_recall_continue_goes_to_sentence_recall(tmp_path):
    session = _at_sentence_recall(tmp_path)
    assert session.step == "sentence-recall"
    assert _log(tmp_path) == ""
    state = session.state()
    assert state["example"] == {"sentence": None, "translation": EXAMPLE["translation"]}
    assert state["sentence_revealed"] is False


def test_example_recall_without_ready_example_logs_and_advances(tmp_path):
    session = _session(tmp_path, FakeExamples(ready=False), mode="example-recall")
    session.submit_answer("zealous")
    session.continue_to_next()
    assert session.step == "recall"
    assert _log(tmp_path).count("item: zealous") == 1


def test_example_mode_never_goes_to_sentence_recall(tmp_path):
    session = _session(tmp_path, FakeExamples(), mode="example")
    session.submit_answer("zealous")
    session.continue_to_next()
    assert session.step == "recall"


def test_reveal_shows_the_sentence(tmp_path):
    session = _at_sentence_recall(tmp_path)
    session.sentence_recall_action("reveal")
    assert session.step == "sentence-recall"
    state = session.state()
    assert state["example"] == EXAMPLE
    assert state["sentence_revealed"] is True
    assert _log(tmp_path) == ""


@pytest.mark.parametrize("mark", ["got", "not_yet"])
def test_marks_log_and_advance(tmp_path, mark):
    session = _at_sentence_recall(tmp_path)
    session.sentence_recall_action("reveal")
    session.sentence_recall_action(mark)
    assert session.step == "recall"
    assert session.correct_count == 1
    log = _log(tmp_path)
    assert log.count("item: zealous") == 1
    assert f"sentence_recall: {mark}" in log


def test_skip_logs_without_a_mark(tmp_path):
    session = _at_sentence_recall(tmp_path)
    session.sentence_recall_action("skip")
    assert session.step == "recall"
    log = _log(tmp_path)
    assert "item: zealous" in log
    assert "sentence_recall" not in log


def test_next_word_hides_the_sentence_again(tmp_path):
    session = _at_sentence_recall(tmp_path)
    session.sentence_recall_action("reveal")
    session.sentence_recall_action("got")
    session.submit_answer("rent")
    session.continue_to_next()
    assert session.state()["example"]["sentence"] is None


def test_sentence_recall_wrong_step_and_bad_mark(tmp_path):
    session = _session(tmp_path, FakeExamples(), mode="example-recall")
    with pytest.raises(WrongStepError):
        session.sentence_recall_action("got")
    session.submit_answer("zealous")
    with pytest.raises(WrongStepError):
        session.sentence_recall_action("got")
    session.continue_to_next()
    with pytest.raises(ValueError):
        session.sentence_recall_action("maybe")
    assert session.step == "sentence-recall"


def test_continue_rejected_at_sentence_recall(tmp_path):
    session = _at_sentence_recall(tmp_path)
    with pytest.raises(WrongStepError):
        session.continue_to_next()


def test_remove_at_sentence_recall_logs_without_a_mark(tmp_path):
    session = _at_sentence_recall(tmp_path)
    session.remove_current(lambda item: None)
    assert session.step == "recall"
    log = _log(tmp_path)
    assert "item: zealous" in log
    assert "sentence_recall" not in log


def test_end_session_at_sentence_recall_logs_nothing(tmp_path):
    session = _session(tmp_path, FakeExamples(), offer_choice=True)
    session.select_collection("unit1", mode="example-recall")
    session.submit_answer("zealous")
    session.continue_to_next()
    session.end_session()
    assert session.step == "choose"
    assert _log(tmp_path) == ""


# --- spec 022: voice and the attempt comparison ---------------------------------


def test_can_transcribe_only_before_reveal_at_sentence_recall(tmp_path):
    session = _session(tmp_path, FakeExamples(), mode="example-recall")
    assert session.can_transcribe() is False  # recall
    session.submit_answer("zealous")
    assert session.can_transcribe() is False  # reveal
    session.continue_to_next()
    assert session.can_transcribe() is True
    session.sentence_recall_action("reveal")
    assert session.can_transcribe() is False
    session.sentence_recall_action("got")
    assert session.can_transcribe() is False


def test_can_transcribe_false_at_choose_and_complete(tmp_path):
    session = _session(tmp_path, FakeExamples(), offer_choice=True)
    assert session.step == "choose"
    assert session.can_transcribe() is False
    session.select_collection(None, mode="recall-only")
    for word in ("zealous", "rent"):
        session.submit_answer(word)
        session.continue_to_next()
    assert session.step == "complete"
    assert session.can_transcribe() is False


@pytest.mark.parametrize("available", [True, False])
def test_voice_available_only_at_sentence_recall(tmp_path, available):
    session = _session(tmp_path, FakeExamples(), mode="example-recall", voice_available=available)
    assert "voice_available" not in session.state()
    session.submit_answer("zealous")
    assert "voice_available" not in session.state()
    session.continue_to_next()
    assert session.state()["voice_available"] is available


def test_voice_available_defaults_to_false(tmp_path):
    session = _at_sentence_recall(tmp_path)
    assert session.state()["voice_available"] is False


def test_reveal_with_attempt_returns_comparison_and_keeps_nothing(tmp_path):
    session = _at_sentence_recall(tmp_path)
    attempt = "She is zelous about recycling"
    comparison = session.sentence_recall_action("reveal", attempt=attempt)
    assert [m.word for m in comparison.sentence if m.status == "missing"] == ["zealous"]
    assert [m.word for m in comparison.attempt if m.status == "extra"] == ["zelous"]
    assert attempt not in repr(vars(session))
    assert "comparison" not in session.state()


@pytest.mark.parametrize("attempt", [None, "", "  "])
def test_reveal_without_attempt_has_no_comparison(tmp_path, attempt):
    session = _at_sentence_recall(tmp_path)
    assert session.sentence_recall_action("reveal", attempt=attempt) is None
    assert session.state()["sentence_revealed"] is True


@pytest.mark.parametrize("mark", ["got", "not_yet", "skip"])
def test_marks_ignore_the_attempt(tmp_path, mark):
    session = _at_sentence_recall(tmp_path)
    session.sentence_recall_action("reveal", attempt="My secret attempt words")
    assert session.sentence_recall_action(mark, attempt="My secret attempt words") is None
    log = _log(tmp_path)
    assert "secret" not in log
    assert log.count("item: zealous") == 1
