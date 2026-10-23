"""CorrectionService (spec 023): background checks on first practice,
saving into own lists or the shared overlay, records, pauses and undo.
The checker is always a fake."""

import hashlib
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from src.models.account import Account
from src.services import corrections_file as cf
from src.services.corrections import (
    AlreadyUndone,
    CorrectionNotFound,
    CorrectionService,
    WordChanged,
)
from src.services.qwen_client import QwenError
from src.services.vocabulary_loader import load_vocabulary
from src.services.word_check import WordCheck
from src.services.word_lists import WordListStore

LILY = Account("lily", "pw", "Lily", Path("pl.md"))
WEIBO = Account("weibo", "pw", "Weibo", Path("pw.md"))

OWN = (
    "---\nenglish: tailor\nipa: ˈteɪlər\npos: [v.]\nalternates: [taylor]\nchinese: 裁缝\n"
    "group: unit1\nexample: The tailor made my suit.\nexample_zh: 裁缝做了我的西装。\n---\n\n"
    "---\nenglish: tidy\nipa: ˈtaɪdi\npos: [adj.]\nalternates: []\nchinese: 整洁的\ngroup: unit1\n---\n\n"
    "---\nenglish: tale\nipa: teɪl\npos: [n.]\nalternates: []\nchinese: 故事\ngroup: unit1\n---\n\n"
    "---\nenglish: tame\nipa: teɪm\npos: [adj.]\nalternates: []\nchinese: 驯服的\ngroup: unit1\n---\n"
)
BRITISH_COPY = (
    "---\nenglish: hot\nipa: hɒt\npos: [adj.]\nalternates: []\nchinese: 热的\ngroup: t\n---\n\n"
    "---\nenglish: tailor\nipa: ˈteɪlə\npos: [n.]\nalternates: []\nchinese: 裁缝\ngroup: t\n---\n"
)
SHARED = (
    "---\nenglish: tailor\nipa: ˈteɪlə\npos: [v.]\nalternates: []\nchinese: 裁缝\ngroup: t-words\n---\n\n"
    "---\nenglish: tidy\nipa: ˈtaɪdi\npos: [adj.]\nalternates: []\nchinese: 整洁的\ngroup: t-words\n---\n"
)
FIXED_TAILOR = WordCheck("ˈteɪlər", "裁缝；定做（衣服）", ["n.", "v."])


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class FakeCheck:
    """Answers per English word; a word missing from *answers* is echoed
    back unchanged. *block* makes calls wait for the event."""

    def __init__(self, answers=None, block: threading.Event | None = None):
        self.answers = answers or {}
        self.block = block
        self.calls: list[tuple] = []
        self.active = 0
        self.most_active = 0
        self._lock = threading.Lock()

    def __call__(self, english, ipa, chinese, pos, dialect):
        with self._lock:
            self.calls.append((english, ipa, chinese, list(pos), dialect))
            self.active += 1
            self.most_active = max(self.most_active, self.active)
        try:
            if self.block is not None:
                self.block.wait(5)
            answer = self.answers.get(english)
            if isinstance(answer, Exception):
                raise answer
            if callable(answer):
                return answer()
            return answer or WordCheck(ipa, chinese, list(pos))
        finally:
            with self._lock:
                self.active -= 1

    def words(self):
        return [c[0] for c in self.calls]


class Clock:
    def __init__(self):
        self.t = 1000.0
        self.wall = datetime(2026, 10, 21, 9, 30, tzinfo=UTC)

    def mono(self):
        return self.t

    def now(self):
        return self.wall

    def advance(self, seconds):
        self.t += seconds
        self.wall += timedelta(seconds=seconds)


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def setup(tmp_path, clock):
    """An own list for Lily and a shared folder; returns a factory for a
    service with a given fake check."""
    vocab = tmp_path / "vocab"
    vocab.mkdir()
    (vocab / "T_words.md").write_text(SHARED, encoding="utf-8")
    store = WordListStore(tmp_path / "word-lists")
    own = store.folder(LILY) / "unit1.md"
    own.parent.mkdir(parents=True)
    own.write_text(OWN, encoding="utf-8")

    def make(check):
        return CorrectionService(
            store, None, shared_dir=vocab, check=check, clock=clock.mono, now=clock.now
        )

    return make, store, own, vocab


def _item(folder: Path, english: str):
    items, _ = load_vocabulary(folder)
    return next(i for i in items if i.english == english)


def _records(folder: Path):
    return cf.read(folder).records


# --- prepare -------------------------------------------------------------------


def test_prepare_returns_at_once_and_checks_once(setup):
    make, _, own, _ = setup
    gate = threading.Event()
    fake = FakeCheck(block=gate)
    service = make(fake)
    item = _item(own.parent, "tidy")
    service.prepare(LILY, item)
    service.prepare(LILY, item)  # same word while its check runs
    gate.set()
    service.wait_all(5)
    service.prepare(LILY, item)  # already checked
    service.wait_all(5)
    assert fake.words() == ["tidy"]


def test_at_most_two_checks_at_once(setup):
    make, _, own, _ = setup
    gate = threading.Event()
    fake = FakeCheck(block=gate)
    service = make(fake)
    for word in ["tailor", "tidy", "tale", "tame"]:
        service.prepare(LILY, _item(own.parent, word))
    for _ in range(50):
        if len(fake.calls) >= 2:
            break
        threading.Event().wait(0.01)
    threading.Event().wait(0.05)
    assert len(fake.calls) == 2
    gate.set()
    service.wait_all(5)
    assert sorted(fake.words()) == ["tailor", "tale", "tame", "tidy"]
    assert fake.most_active == 2


def test_disabled_service_checks_nothing(setup):
    _, store, own, vocab = setup
    service = CorrectionService(store, None, shared_dir=vocab)
    assert service.enabled is False
    service.prepare(LILY, _item(own.parent, "tidy"))
    service.wait_all(5)
    assert cf.read(own.parent).checked == []


# --- own lists -------------------------------------------------------------------


def test_own_list_correction_is_written_into_the_block(setup):
    make, _, own, _ = setup
    service = make(FakeCheck({"tailor": FIXED_TAILOR}))
    item = _item(own.parent, "tailor")
    service.prepare(LILY, item)
    service.wait_all(5)

    text = own.read_text(encoding="utf-8")
    expected = OWN.replace(
        "pos: [v.]\nalternates: [taylor]\nchinese: 裁缝\n",
        "pos: [n., v.]\nalternates: [taylor]\nchinese: 裁缝；定做（衣服）\n",
    )
    assert text == expected
    items, warnings = load_vocabulary(own.parent)
    assert warnings == []
    tailor = next(i for i in items if i.english == "tailor")
    assert tailor.alternates == ["taylor"] and tailor.example == "The tailor made my suit."


def test_own_list_records_one_per_changed_field(setup):
    make, _, own, _ = setup
    service = make(FakeCheck({"tailor": FIXED_TAILOR}))
    service.prepare(LILY, _item(own.parent, "tailor"))
    service.wait_all(5)

    records = _records(own.parent)
    assert {r.field for r in records} == {"chinese", "pos"}
    assert len({r.batch for r in records}) == 1
    by_field = {r.field: r for r in records}
    assert (by_field["chinese"].old, by_field["chinese"].new) == ("裁缝", "裁缝；定做（衣服）")
    assert (by_field["pos"].old, by_field["pos"].new) == (["v."], ["n.", "v."])
    record = by_field["chinese"]
    assert (record.file, record.group, record.english, record.origin_chinese) == (
        "unit1.md",
        "unit1",
        "tailor",
        "裁缝",
    )
    assert record.at == "2026-10-21T09:30:00Z" and record.undone_at is None


def test_live_item_is_updated_in_place(setup):
    make, _, own, _ = setup
    service = make(FakeCheck({"tailor": FIXED_TAILOR}))
    item = _item(own.parent, "tailor")
    bound = service.bind(LILY)
    bound.prepare(item)
    service.wait_all(5)
    assert (item.chinese, item.pos, item.origin_chinese) == (
        "裁缝；定做（衣服）",
        ["n.", "v."],
        "裁缝；定做（衣服）",
    )
    assert bound.corrected_fields(item) == ["chinese", "pos"]
    assert bound.corrected_fields(_item(own.parent, "tidy")) == []


def test_right_word_is_left_alone_but_marked_checked(setup):
    make, _, own, _ = setup
    service = make(FakeCheck({"tidy": WordCheck("/ˈtaɪdi/", " 整洁的 ", ["adjective"])}))
    service.prepare(LILY, _item(own.parent, "tidy"))
    service.wait_all(5)
    assert own.read_text(encoding="utf-8") == OWN
    assert _records(own.parent) == []
    assert len(cf.read(own.parent).checked) == 1


def test_checked_words_are_not_sent_again_after_restart(setup):
    make, _, own, _ = setup
    first = make(FakeCheck({"tailor": FIXED_TAILOR}))
    first.prepare(LILY, _item(own.parent, "tailor"))
    first.wait_all(5)

    again = FakeCheck()
    fresh = make(again)  # a new process: only the files remember
    fresh.prepare(LILY, _item(own.parent, "tailor"))
    fresh.prepare(LILY, _item(own.parent, "tidy"))
    fresh.wait_all(5)
    assert again.words() == ["tidy"]


def test_edited_word_is_checked_again(setup):
    make, _, own, _ = setup
    fake = FakeCheck()
    service = make(fake)
    service.prepare(LILY, _item(own.parent, "tidy"))
    service.wait_all(5)
    own.write_text(OWN.replace("整洁的", "整齐的"), encoding="utf-8")
    service.prepare(LILY, _item(own.parent, "tidy"))
    service.wait_all(5)
    assert fake.words() == ["tidy", "tidy"]


def test_word_edited_during_the_check_is_not_overwritten(setup):
    make, _, own, _ = setup
    gate = threading.Event()
    service = make(FakeCheck({"tailor": FIXED_TAILOR}, block=gate))
    service.prepare(LILY, _item(own.parent, "tailor"))
    edited = OWN.replace("chinese: 裁缝\n", "chinese: 裁缝；我改的\n")
    own.write_text(edited, encoding="utf-8")
    gate.set()
    service.wait_all(5)
    assert own.read_text(encoding="utf-8") == edited
    assert _records(own.parent) == []


def test_word_removed_during_the_check_is_skipped(setup):
    make, _, own, _ = setup
    gate = threading.Event()
    service = make(FakeCheck({"tailor": FIXED_TAILOR}, block=gate))
    service.prepare(LILY, _item(own.parent, "tailor"))
    without = OWN.split("\n\n", 1)[1]
    own.write_text(without, encoding="utf-8")
    gate.set()
    service.wait_all(5)
    assert own.read_text(encoding="utf-8") == without
    assert _records(own.parent) == []


# --- dialect (R3, per file) ------------------------------------------------------------


def test_american_list_is_checked_as_american(setup):
    make, _, own, _ = setup
    fake = FakeCheck()
    service = make(fake)
    service.prepare(LILY, _item(own.parent, "tidy"))
    service.wait_all(5)
    assert fake.calls[0][4] == "american"


def test_list_copied_from_the_shared_sets_is_british(setup):
    make, _, own, _ = setup
    copy = own.parent / "copied.md"
    copy.write_text(BRITISH_COPY, encoding="utf-8")
    fake = FakeCheck()
    service = make(fake)
    # ˈteɪlə passes both checks; hɒt in the same file makes the file British.
    item = next(
        i for i in load_vocabulary(own.parent)[0] if i.source == copy and i.english == "tailor"
    )
    service.prepare(LILY, item)
    service.wait_all(5)
    assert fake.calls[0][4] == "british"


# --- failures and pauses (R8) ------------------------------------------------------------


@pytest.mark.parametrize("code", ["bad_reply", "bad_status"])
def test_bad_answer_affects_that_word_only(setup, code):
    make, _, own, _ = setup
    fake = FakeCheck({"tailor": QwenError(code)})
    service = make(fake)
    service.prepare(LILY, _item(own.parent, "tailor"))
    service.wait_all(5)
    assert own.read_text(encoding="utf-8") == OWN
    assert cf.read(own.parent).checked == []
    assert service.paused() is None
    service.prepare(LILY, _item(own.parent, "tailor"))
    service.prepare(LILY, _item(own.parent, "tidy"))
    service.wait_all(5)
    assert sorted(fake.words()) == ["tailor", "tailor", "tidy"]


@pytest.mark.parametrize("code", ["timeout", "unavailable", "rate_limited"])
def test_provider_trouble_pauses_for_five_minutes(setup, clock, code):
    make, _, own, _ = setup
    fake = FakeCheck({"tailor": QwenError(code)})
    service = make(fake)
    service.prepare(LILY, _item(own.parent, "tailor"))
    service.wait_all(5)
    assert service.paused() == {"reason": str(QwenError(code)), "until": "2026-10-21T09:35:00Z"}
    service.prepare(LILY, _item(own.parent, "tidy"))
    service.wait_all(5)
    assert fake.words() == ["tailor"]

    clock.advance(301)
    assert service.paused() is None
    service.prepare(LILY, _item(own.parent, "tidy"))
    service.wait_all(5)
    assert fake.words() == ["tailor", "tidy"]


def test_rejected_key_pauses_until_restart(setup, clock):
    make, _, own, _ = setup
    fake = FakeCheck({"tailor": QwenError("auth")})
    service = make(fake)
    service.prepare(LILY, _item(own.parent, "tailor"))
    service.wait_all(5)
    clock.advance(10_000)
    assert service.paused() == {"reason": "Qwen rejected the API key.", "until": None}
    service.prepare(LILY, _item(own.parent, "tidy"))
    service.wait_all(5)
    assert fake.words() == ["tailor"]


def test_unexpected_error_is_contained(setup):
    make, _, own, _ = setup
    fake = FakeCheck({"tailor": RuntimeError("boom")})
    service = make(fake)
    service.prepare(LILY, _item(own.parent, "tailor"))
    service.wait_all(5)
    assert own.read_text(encoding="utf-8") == OWN
    assert service.paused() is None
    assert cf.read(own.parent).checked == []


def test_logs_never_hold_values_or_answers(setup, caplog):
    make, _, own, _ = setup
    service = make(FakeCheck({"tailor": FIXED_TAILOR, "tidy": QwenError("bad_reply")}))
    with caplog.at_level("DEBUG"):
        service.prepare(LILY, _item(own.parent, "tailor"))
        service.prepare(LILY, _item(own.parent, "tidy"))
        service.wait_all(5)
    assert "定做" not in caplog.text and "裁缝" not in caplog.text and "整洁" not in caplog.text


# --- listing ---------------------------------------------------------------------------


def test_list_shows_own_records_newest_first(setup, clock):
    make, _, own, _ = setup
    other = WordCheck("ˈtaɪdi", "整洁的；整齐的", ["adj."])
    service = make(FakeCheck({"tailor": FIXED_TAILOR, "tidy": other}))
    service.prepare(LILY, _item(own.parent, "tailor"))
    service.wait_all(5)
    clock.advance(60)
    service.prepare(LILY, _item(own.parent, "tidy"))
    service.wait_all(5)

    entries = service.bind(LILY).list()
    assert [(e["english"], e["field"]) for e in entries] == [
        ("tidy", "chinese"),
        ("tailor", "chinese"),
        ("tailor", "pos"),
    ]
    first = entries[0]
    assert set(first) == {
        "id",
        "scope",
        "english",
        "list",
        "field",
        "old",
        "new",
        "at",
        "undone",
        "can_undo",
    }
    assert (first["scope"], first["list"], first["undone"], first["can_undo"]) == (
        "own",
        "unit1.md",
        False,
        True,
    )
    assert service.bind(WEIBO).list() == []


# --- undo (US2) ------------------------------------------------------------------------


def _corrected_tailor(make, own):
    service = make(FakeCheck({"tailor": FIXED_TAILOR}))
    item = _item(own.parent, "tailor")
    service.prepare(LILY, item)
    service.wait_all(5)
    return service, item


def test_undo_restores_every_field_of_the_batch(setup):
    make, _, own, _ = setup
    service, _ = _corrected_tailor(make, own)
    record_id = _records(own.parent)[0].id
    assert service.undo(LILY, record_id) == ["chinese", "pos"]
    assert own.read_text(encoding="utf-8") == OWN
    records = _records(own.parent)
    assert all(r.undone_at == "2026-10-21T09:30:00Z" for r in records)
    entries = service.bind(LILY).list()
    assert all(e["undone"] and not e["can_undo"] for e in entries)


def test_undone_change_never_comes_back(setup):
    make, _, own, _ = setup
    service, _ = _corrected_tailor(make, own)
    service.undo(LILY, _records(own.parent)[0].id)
    again = FakeCheck({"tailor": FIXED_TAILOR})
    fresh = make(again)
    fresh.prepare(LILY, _item(own.parent, "tailor"))
    fresh.wait_all(5)
    assert again.calls == []
    assert own.read_text(encoding="utf-8") == OWN


def test_undo_errors(setup):
    make, _, own, _ = setup
    service, _ = _corrected_tailor(make, own)
    with pytest.raises(CorrectionNotFound):
        service.undo(LILY, "ffffffffffff")
    with pytest.raises(CorrectionNotFound):
        service.undo(WEIBO, _records(own.parent)[0].id)  # not one Weibo can see
    record_id = _records(own.parent)[0].id
    service.undo(LILY, record_id)
    with pytest.raises(AlreadyUndone):
        service.undo(LILY, record_id)


def test_undo_refuses_after_the_word_was_edited(setup):
    make, _, own, _ = setup
    service, _ = _corrected_tailor(make, own)
    edited = own.read_text(encoding="utf-8").replace("裁缝；定做（衣服）", "裁缝；我改的")
    own.write_text(edited, encoding="utf-8")
    assert all(not e["can_undo"] for e in service.bind(LILY).list())
    with pytest.raises(WordChanged):
        service.undo(LILY, _records(own.parent)[0].id)
    assert own.read_text(encoding="utf-8") == edited
    assert all(r.undone_at is None for r in _records(own.parent))


def test_undo_refuses_after_the_word_was_removed(setup):
    make, _, own, _ = setup
    service, _ = _corrected_tailor(make, own)
    own.write_text(own.read_text(encoding="utf-8").split("\n\n", 1)[1], encoding="utf-8")
    with pytest.raises(WordChanged):
        service.undo(LILY, _records(own.parent)[0].id)


def test_undo_updates_the_live_item(setup):
    make, _, own, _ = setup
    service, item = _corrected_tailor(make, own)
    service.undo(LILY, _records(own.parent)[0].id, live_items=[item])
    assert (item.chinese, item.pos, item.origin_chinese) == ("裁缝", ["v."], "裁缝")
    assert service.corrected_fields(item) == []


def test_undo_works_without_a_key(setup, tmp_path):
    make, store, own, vocab = setup
    _corrected_tailor(make, own)
    keyless = CorrectionService(store, None, shared_dir=vocab)
    keyless.undo(LILY, _records(own.parent)[0].id)
    assert own.read_text(encoding="utf-8") == OWN


# --- shared sets (US3) -----------------------------------------------------------------

SHARED_TAILOR = WordCheck("ˈteɪlə", "裁缝；定做（衣服）", ["n.", "v."])


def _shared_item(vocab: Path, english: str):
    return _item(vocab, english)


def test_shared_word_is_checked_as_british_and_saved_in_the_overlay(setup):
    make, _, _, vocab = setup
    before = sha(vocab / "T_words.md")
    fake = FakeCheck({"tailor": SHARED_TAILOR})
    service = make(fake)
    item = _shared_item(vocab, "tailor")
    service.prepare(WEIBO, item)
    service.wait_all(5)

    assert fake.calls[0][4] == "british"
    assert sha(vocab / "T_words.md") == before
    data = cf.read(vocab)
    key = cf.overlay_key("T_words.md", "t-words", "tailor", "裁缝")
    assert data.overlay[key] == cf.WordValues.normal("ˈteɪlə", "裁缝；定做（衣服）", ["n.", "v."])
    assert {r.field for r in data.records} == {"chinese", "pos"}
    assert all(r.origin_chinese == "裁缝" for r in data.records)
    # The live item shows the correction but keeps its file meaning.
    assert (item.chinese, item.origin_chinese) == ("裁缝；定做（衣服）", "裁缝")
    # Everyone's next load shows it.
    assert _shared_item(vocab, "tailor").chinese == "裁缝；定做（衣服）"


def test_shared_word_checked_for_one_learner_is_not_sent_for_another(setup):
    make, _, _, vocab = setup
    fake = FakeCheck({"tailor": SHARED_TAILOR})
    service = make(fake)
    stale = _shared_item(vocab, "tailor")  # loaded before the correction
    service.prepare(WEIBO, _shared_item(vocab, "tailor"))
    service.wait_all(5)
    service.prepare(WEIBO, _shared_item(vocab, "tailor"))  # corrected values
    service.prepare(Account("amy", "pw", "Amy", Path("pa.md")), stale)
    service.wait_all(5)
    assert fake.words() == ["tailor"]


def test_shared_word_changed_meanwhile_is_not_saved(setup):
    make, _, _, vocab = setup
    gate = threading.Event()
    service = make(FakeCheck({"tailor": SHARED_TAILOR}, block=gate))
    service.prepare(WEIBO, _shared_item(vocab, "tailor"))
    key = cf.overlay_key("T_words.md", "t-words", "tailor", "裁缝")
    other = cf.WordValues.normal("ˈteɪlə", "裁缝；别人改的", ["n."])

    def put(data):
        data.overlay[key] = other

    cf.update(vocab, put)
    gate.set()
    service.wait_all(5)
    data = cf.read(vocab)
    assert data.overlay[key] == other
    assert data.records == []


def test_shared_undo_applies_to_everyone(setup):
    make, _, _, vocab = setup
    service = make(FakeCheck({"tailor": SHARED_TAILOR}))
    service.prepare(WEIBO, _shared_item(vocab, "tailor"))
    service.wait_all(5)
    record_id = cf.read(vocab).records[0].id
    amy = Account("amy", "pw", "Amy", Path("pa.md"))
    assert service.undo(amy, record_id) == ["chinese", "pos"]

    data = cf.read(vocab)
    assert data.overlay == {}  # back to the file's values
    assert all(r.undone_at for r in data.records)
    assert _shared_item(vocab, "tailor").chinese == "裁缝"
    again = FakeCheck({"tailor": SHARED_TAILOR})
    fresh = make(again)
    fresh.prepare(WEIBO, _shared_item(vocab, "tailor"))
    fresh.wait_all(5)
    assert again.calls == []


def test_shared_correction_of_one_field_is_stored_whole_and_undone(setup):
    make, _, _, vocab = setup
    service = make(FakeCheck({"tailor": WordCheck("ˈteɪlə", "裁缝", ["n.", "v."])}))
    service.prepare(WEIBO, _shared_item(vocab, "tailor"))
    service.wait_all(5)
    key = cf.overlay_key("T_words.md", "t-words", "tailor", "裁缝")
    # The entry holds all three fields, though only pos changed.
    assert cf.read(vocab).overlay[key] == cf.WordValues.normal("ˈteɪlə", "裁缝", ["n.", "v."])
    assert [r.field for r in cf.read(vocab).records] == ["pos"]
    service.undo(WEIBO, cf.read(vocab).records[0].id)
    assert key not in cf.read(vocab).overlay


def test_shared_records_are_listed_only_for_shared_learners(setup):
    make, _, _, vocab = setup
    service = make(FakeCheck({"tailor": SHARED_TAILOR}))
    service.prepare(WEIBO, _shared_item(vocab, "tailor"))
    service.wait_all(5)
    entries = service.bind(WEIBO).list()
    assert {(e["scope"], e["field"]) for e in entries} == {("shared", "chinese"), ("shared", "pos")}
    assert all(e["list"] == "T_words.md" and e["can_undo"] for e in entries)
    # Lily practises her own lists, so the shared records aren't hers.
    assert service.bind(LILY).list() == []
    with pytest.raises(CorrectionNotFound):
        service.undo(LILY, entries[0]["id"])


def test_word_outside_both_folders_is_not_checked(setup, tmp_path):
    make, _, _, _ = setup
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / "x.md").write_text(SHARED, encoding="utf-8")
    fake = FakeCheck()
    service = make(fake)
    service.prepare(WEIBO, _item(elsewhere, "tailor"))
    service.wait_all(5)
    assert fake.calls == []
