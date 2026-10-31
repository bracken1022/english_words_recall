"""The missed-words list on the completion screen (spec 024, data-model.md):
words whose word answer was wrong in the set just finished, in order, with
the learner's answer, built from the live items at "complete"."""

from pathlib import Path

from src.web.session_state import PracticeSession

VOCAB = (
    "---\nenglish: tailor\nchinese: 裁缝\nipa: ˈteɪlə\npos: [n., v.]\ngroup: unit1\n---\n\n"
    "---\nenglish: bank\nchinese: 银行\nipa: bæŋk\npos: [n.]\ngroup: unit1\n---\n\n"
    "---\nenglish: bank\nchinese: 河岸\nipa: bæŋk\npos: [n.]\ngroup: unit1\n---\n\n"
    "---\nenglish: tidy\nchinese: 整洁的\ngroup: unit1\n---\n\n"
    "---\nenglish: rent\nchinese: 租金\ngroup: unit2\n---\n"
)
EXAMPLE = {"sentence": "The tailor made my suit.", "translation": "裁缝做了我的西装。"}


class FakeExamples:
    def prepare(self, item):
        pass

    def get(self, item):
        return dict(EXAMPLE)

    def status(self, item):
        return "ready"


def _session(tmp_path: Path, **kwargs) -> PracticeSession:
    vocab = tmp_path / "vocab"
    vocab.mkdir(exist_ok=True)
    (vocab / "words.md").write_text(VOCAB, encoding="utf-8")
    return PracticeSession(vocab_dir=vocab, progress_file=tmp_path / "progress.md", **kwargs)


def _chosen(tmp_path: Path, group="unit1", mode="recall-only", **kwargs) -> PracticeSession:
    session = _session(tmp_path, offer_choice=True, **kwargs)
    session.select_collection(group, mode=mode)
    return session


def _answer(session: PracticeSession, answer: str) -> None:
    session.submit_answer(answer)
    session.continue_to_next()


def _play(session: PracticeSession, answers: list[str]) -> dict:
    for answer in answers:
        _answer(session, answer)
    state = session.state()
    assert state["step"] == "complete"
    return state


def test_wrong_answers_are_listed_in_order(tmp_path):
    state = _play(_chosen(tmp_path), ["tailer", "bank", "bang", "tidy"])
    assert state["missed"] == [
        {
            "english": "tailor",
            "ipa": "ˈteɪlə",
            "pos": ["n.", "v."],
            "chinese": "裁缝",
            "answer": "tailer",
            "shown": False,
        },
        {
            "english": "bank",
            "ipa": "bæŋk",
            "pos": ["n."],
            "chinese": "河岸",
            "answer": "bang",
            "shown": False,
        },
    ]
    assert len(state["missed"]) == state["total"] - state["correct"]


def test_all_right_gives_an_empty_list(tmp_path):
    state = _play(_chosen(tmp_path), ["tailor", "bank", "bank", "tidy"])
    assert state["missed"] == []


def test_shown_answers(tmp_path):
    state = _play(_chosen(tmp_path), ["", "   ", "bank", "tidy"])
    assert [(m["english"], m["answer"], m["shown"]) for m in state["missed"]] == [
        ("tailor", None, True),
        ("bank", None, True),
    ]


def test_two_meanings_of_one_word_are_two_entries(tmp_path):
    state = _play(_chosen(tmp_path), ["tailor", "x", "y", "tidy"])
    assert [(m["english"], m["chinese"], m["answer"]) for m in state["missed"]] == [
        ("bank", "银行", "x"),
        ("bank", "河岸", "y"),
    ]


def test_missing_ipa_and_pos(tmp_path):
    state = _play(_chosen(tmp_path), ["tailor", "bank", "bank", "tiddy"])
    assert state["missed"][0]["english"] == "tidy"
    assert state["missed"][0]["ipa"] is None
    assert state["missed"][0]["pos"] == []


def test_sentence_marks_never_change_the_list(tmp_path):
    session = _chosen(tmp_path, mode="example-recall", example_service=FakeExamples())
    for answer, mark in [("tailor", "not_yet"), ("x", "got"), ("bank", "skip"), ("tidy", "got")]:
        session.submit_answer(answer)
        session.continue_to_next()
        assert session.step == "sentence-recall"
        session.sentence_recall_action(mark)
    state = session.state()
    assert state["step"] == "complete"
    assert [(m["english"], m["chinese"]) for m in state["missed"]] == [("bank", "银行")]


def test_a_word_removed_after_a_wrong_answer_is_not_listed(tmp_path):
    session = _chosen(tmp_path)
    session.submit_answer("tailer")
    session.remove_current(lambda item: None)
    state = _play(session, ["x", "bank", "tidy"])
    assert [m["chinese"] for m in state["missed"]] == ["银行"]
    assert len(state["missed"]) == state["total"] - state["correct"]


def test_a_removed_word_brought_back_and_missed_is_listed_once(tmp_path):
    session = _chosen(tmp_path)
    session.submit_answer("tailer")
    session.remove_current(lambda item: "token")
    session.undo_remove(lambda token: None)
    state = _play(session, ["taylor", "bank", "bank", "tidy"])
    assert [(m["english"], m["answer"]) for m in state["missed"]] == [("tailor", "taylor")]


def test_a_new_set_starts_a_new_list(tmp_path):
    session = _chosen(tmp_path)
    _play(session, ["x", "bank", "bank", "tidy"])
    session.restart()
    session.select_collection("unit2", mode="recall-only")
    state = _play(session, ["rant"])
    assert [m["english"] for m in state["missed"]] == ["rent"]


def test_end_session_shows_no_list_and_the_next_set_starts_empty(tmp_path):
    session = _chosen(tmp_path)
    _answer(session, "x")
    session.submit_answer("y")
    session.end_session()
    assert session.step == "choose"
    assert "missed" not in session.state()
    session.select_collection("unit2", mode="recall-only")
    assert _play(session, ["rent"])["missed"] == []


def test_a_locked_session_lists_misses(tmp_path):
    session = _session(tmp_path, group="unit2", mode="recall-only")
    assert [m["english"] for m in _play(session, ["rant"])["missed"]] == ["rent"]


def test_entries_show_the_current_corrected_values(tmp_path):
    session = _chosen(tmp_path)
    tailor = session.current_item
    _answer(session, "x")
    # As a spec 023 correction does, after the answer.
    tailor.chinese, tailor.ipa, tailor.pos = "裁缝；定做（衣服）", "ˈteɪlər", ["n."]
    state = _play(session, ["bank", "bank", "tidy"])
    assert state["missed"][0]["chinese"] == "裁缝；定做（衣服）"
    assert state["missed"][0]["ipa"] == "ˈteɪlər"
    assert state["missed"][0]["pos"] == ["n."]


def test_missed_is_only_in_the_complete_state(tmp_path):
    session = _chosen(tmp_path)
    assert "missed" not in session.state()
    session.submit_answer("x")
    assert "missed" not in session.state()
