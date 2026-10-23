"""End-to-end word corrections (spec 023, quickstart): practise, correct in
the background, reveal, list, undo, and never re-send. Qwen is faked."""

import hashlib
import threading
from pathlib import Path

from src.models.account import Account
from src.services.word_check import WordCheck
from src.web.app import create_app

SHARED = (
    "---\nenglish: tailor\nipa: ˈteɪlə\npos: [v.]\nalternates: []\nchinese: 裁缝\ngroup: t-words\n---\n\n"
    "---\nenglish: tidy\nipa: ˈtaɪdi\npos: [adj.]\nalternates: []\nchinese: 整洁的\ngroup: t-words\n---\n"
)
OWN = (
    "---\nenglish: zealous\nipa: ˈzeləs\npos: [n.]\nalternates: [zelous]\nchinese: 嫉妒的\ngroup: unit1\n"
    "example: She is zealous about recycling.\nexample_zh: 她热衷于回收利用。\n---\n\n"
    "---\nenglish: rent\nipa: rent\npos: [n.]\nalternates: []\nchinese: 租金\ngroup: unit1\n---\n"
)
ZEALOUS = WordCheck("ˈzeləs", "热心的；狂热的", ["adj."])
ACCOUNTS_ARGS = ("lily", "weibo")


class FakeCheck:
    def __init__(self, answers=None):
        self.answers = answers or {}
        self.calls = []
        self.gate: threading.Event | None = None

    def __call__(self, english, ipa, chinese, pos, dialect):
        self.calls.append(english)
        if self.gate is not None:
            self.gate.wait(5)
        return self.answers.get(english) or WordCheck(ipa, chinese, list(pos))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _setup(tmp_path: Path, own: bool = True):
    vocab = tmp_path / "vocab"
    vocab.mkdir(exist_ok=True)
    if not (vocab / "T_words.md").exists():
        (vocab / "T_words.md").write_text(SHARED, encoding="utf-8")
    own_file = tmp_path / "wl" / "lily" / "unit1.md"
    if own and not own_file.exists():
        own_file.parent.mkdir(parents=True)
        own_file.write_text(OWN, encoding="utf-8")
    return vocab, own_file


def _app(tmp_path: Path, check):
    vocab, _ = _setup(tmp_path)
    return create_app(
        vocab_dir=vocab,
        progress_file=tmp_path / "p.md",
        offer_choice=True,
        accounts=[Account(name, "pw", name, tmp_path / f"p-{name}.md") for name in ACCOUNTS_ARGS],
        word_lists_dir=tmp_path / "wl",
        correction_check=check,
    )


def _login(app, user="lily"):
    client = app.test_client()
    client.post("/api/login", json={"username": user, "password": "pw"})
    return client


def test_own_list_word_corrects_itself_and_is_not_resent(tmp_path):
    fake = FakeCheck({"zealous": ZEALOUS})
    app = _app(tmp_path, fake)
    client = _login(app)
    client.post("/api/select", json={"collection": "unit1", "mode": "recall-only"})
    app.correction_service.wait_all(5)
    client.post("/api/answer", json={"answer": "zelus"})
    state = client.get("/api/state").get_json()
    assert (state["chinese"], state["pos"], state["corrected"]) == (
        "热心的；狂热的",
        ["adj."],
        ["chinese", "pos"],
    )

    own_file = tmp_path / "wl" / "lily" / "unit1.md"
    text = own_file.read_text(encoding="utf-8")
    # English, alternates and example lines unchanged (SC-007).
    assert "english: zealous\n" in text and "alternates: [zelous]\n" in text
    assert "example: She is zealous about recycling.\nexample_zh: 她热衷于回收利用。\n" in text
    assert "chinese: 热心的；狂热的\n" in text and "pos: [adj.]\n" in text

    # A new process practising the same words sends nothing for zealous (SC-005).
    again = FakeCheck()
    app2 = _app(tmp_path, again)
    client2 = _login(app2)
    client2.post("/api/select", json={"collection": "unit1", "mode": "recall-only"})
    app2.correction_service.wait_all(5)
    assert "zealous" not in again.calls


def test_answering_before_the_check_finishes_never_waits(tmp_path):
    fake = FakeCheck({"zealous": ZEALOUS})
    fake.gate = threading.Event()
    app = _app(tmp_path, fake)
    client = _login(app)
    client.post("/api/select", json={"collection": "unit1", "mode": "recall-only"})
    client.post("/api/answer", json={"answer": "zelus"})  # check still blocked
    state = client.get("/api/state").get_json()
    assert state["step"] == "reveal" and state["chinese"] == "嫉妒的"
    assert state["corrected"] == []
    fake.gate.set()
    app.correction_service.wait_all(5)

    # The next load of the list shows the corrected values.
    fresh = _login(_app(tmp_path, FakeCheck()))
    fresh.post("/api/select", json={"collection": "unit1", "mode": "recall-only"})
    assert fresh.get("/api/state").get_json()["chinese"] == "热心的；狂热的"


def test_undone_correction_stays_undone(tmp_path):
    app = _app(tmp_path, FakeCheck({"zealous": ZEALOUS}))
    client = _login(app)
    client.post("/api/select", json={"collection": "unit1", "mode": "recall-only"})
    app.correction_service.wait_all(5)
    entry = client.get("/api/corrections").get_json()["corrections"][0]
    assert client.post("/api/corrections/undo", json={"id": entry["id"]}).status_code == 200
    own_file = tmp_path / "wl" / "lily" / "unit1.md"
    assert own_file.read_text(encoding="utf-8") == OWN

    # Practised again in a new process: not sent, not changed (SC-004).
    again = FakeCheck({"zealous": ZEALOUS})
    app2 = _app(tmp_path, again)
    client2 = _login(app2)
    client2.post("/api/select", json={"collection": "unit1", "mode": "recall-only"})
    app2.correction_service.wait_all(5)
    assert "zealous" not in again.calls
    assert client2.get("/api/state").get_json()["chinese"] == "嫉妒的"


# --- shared sets (US3) ----------------------------------------------------------------------

TAILOR = WordCheck("ˈteɪlə", "裁缝；定做（衣服）", ["n.", "v."])


def _shared_app(tmp_path: Path, check):
    vocab, _ = _setup(tmp_path, own=False)
    return create_app(
        vocab_dir=vocab,
        progress_file=tmp_path / "p.md",
        offer_choice=True,
        accounts=[Account(name, "pw", name, tmp_path / f"p-{name}.md") for name in ACCOUNTS_ARGS],
        word_lists_dir=tmp_path / "wl",
        correction_check=check,
    )


def test_shared_correction_shows_for_everyone_and_files_stay_unchanged(tmp_path):
    vocab, _ = _setup(tmp_path, own=False)
    before = sha(vocab / "T_words.md")
    fake = FakeCheck({"tailor": TAILOR})
    app = _shared_app(tmp_path, fake)
    lily = _login(app, "lily")
    lily.post("/api/select", json={"collection": "t-words", "mode": "recall-only"})
    app.correction_service.wait_all(5)

    weibo = _login(app, "weibo")
    weibo.post("/api/select", json={"collection": "t-words", "mode": "recall-only"})
    app.correction_service.wait_all(5)
    assert weibo.get("/api/state").get_json()["chinese"] == "裁缝；定做（衣服）"
    assert fake.calls.count("tailor") == 1
    assert sha(vocab / "T_words.md") == before

    # Lily undoes it; Weibo's next session shows the file's meaning.
    entry = lily.get("/api/corrections").get_json()["corrections"][0]
    assert lily.post("/api/corrections/undo", json={"id": entry["id"]}).status_code == 200
    fresh = _login(_shared_app(tmp_path, FakeCheck()), "weibo")
    fresh.post("/api/select", json={"collection": "t-words", "mode": "recall-only"})
    assert fresh.get("/api/state").get_json()["chinese"] == "裁缝"
    assert sha(vocab / "T_words.md") == before


def test_corrected_shared_word_can_be_removed_and_restored(tmp_path):
    app = _shared_app(tmp_path, FakeCheck({"tailor": TAILOR}))
    lily = _login(app, "lily")
    lily.post("/api/select", json={"collection": "t-words", "mode": "recall-only"})
    app.correction_service.wait_all(5)
    assert lily.post("/api/remove-word").status_code == 200
    # Hidden in a new session (keyed by the file meaning).
    fresh_app = _shared_app(tmp_path, FakeCheck())
    fresh = _login(fresh_app, "lily")
    fresh.post("/api/select", json={"collection": "t-words", "mode": "recall-only"})
    state = fresh.get("/api/state").get_json()
    assert state["chinese"] == "整洁的" and state["total"] == 1

    assert lily.post("/api/undo-remove").status_code == 200
    again = _login(_shared_app(tmp_path, FakeCheck()), "lily")
    again.post("/api/select", json={"collection": "t-words", "mode": "recall-only"})
    assert again.get("/api/state").get_json()["total"] == 2


def test_corrected_shared_word_keeps_its_saved_example(tmp_path):
    vocab, _ = _setup(tmp_path, own=False)
    (vocab / ".examples.json").write_text(
        '{"version": 1, "examples": {"t-words|tailor|裁缝": '
        '{"sentence": "The tailor fixed my coat.", "translation": "裁缝修好了我的外套。"}}}',
        encoding="utf-8",
    )
    app = _shared_app(tmp_path, FakeCheck({"tailor": TAILOR}))
    lily = _login(app, "lily")
    lily.post("/api/select", json={"collection": "t-words", "mode": "example"})
    app.correction_service.wait_all(5)
    lily.post("/api/answer", json={"answer": "tailor"})
    state = lily.get("/api/state").get_json()
    assert state["chinese"] == "裁缝；定做（衣服）"
    assert state["example"]["sentence"] == "The tailor fixed my coat."
