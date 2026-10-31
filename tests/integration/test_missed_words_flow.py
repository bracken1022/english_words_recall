"""Finishing a set over HTTP lists the missed words (spec 024, quickstart
a, c, d), and progress logging is unchanged (FR-012)."""

from pathlib import Path

from src.web.app import create_app

VOCAB = (
    "---\nenglish: tailor\nchinese: 裁缝\nipa: ˈteɪlə\npos: [n.]\ngroup: unit1\n---\n\n"
    "---\nenglish: zealous\nchinese: 热心的\npos: [adj.]\ngroup: unit1\n---\n\n"
    "---\nenglish: rent\nchinese: 租金\ngroup: unit1\n---\n\n"
    "---\nenglish: tyre\nchinese: 轮胎\ngroup: unit1\n---\n\n"
    "---\nenglish: tidy\nchinese: 整洁的\ngroup: unit1\n---\n\n"
    "---\nenglish: sack\nchinese: 解雇\ngroup: unit2\n---\n"
)


def _client(tmp_path: Path):
    vocab = tmp_path / "vocab"
    vocab.mkdir()
    (vocab / "words.md").write_text(VOCAB, encoding="utf-8")
    app = create_app(vocab_dir=vocab, progress_file=tmp_path / "progress.md", offer_choice=True)
    return app.test_client()


def _play(client, answers):
    for answer in answers:
        assert client.post("/api/answer", json={"answer": answer}).status_code == 200
        assert client.post("/api/continue").status_code == 200
    return client.get("/api/state").get_json()


def test_finishing_a_set_lists_the_missed_words(tmp_path):
    client = _client(tmp_path)
    client.post("/api/select", json={"collection": "unit1", "mode": "recall-only"})
    state = _play(client, ["tailer", "zealous", "", "tire", "tidy"])

    assert state["step"] == "complete"
    assert (state["correct"], state["total"]) == (2, 5)
    assert [(m["english"], m["answer"], m["shown"]) for m in state["missed"]] == [
        ("tailor", "tailer", False),
        ("rent", None, True),
        ("tyre", "tire", False),
    ]
    assert state["missed"][0]["ipa"] == "ˈteɪlə"
    assert state["missed"][0]["pos"] == ["n."]

    # A reload fetches the same list (FR-008).
    assert client.get("/api/state").get_json()["missed"] == state["missed"]

    # Progress has one entry per answered word, as before (FR-012).
    log = (tmp_path / "progress.md").read_text(encoding="utf-8")
    for word in ("tailor", "zealous", "rent", "tyre", "tidy"):
        assert log.count(f"item: {word}\n") == 1

    # The next set has its own list (FR-005).
    assert client.post("/api/restart").status_code == 200
    client.post("/api/select", json={"collection": "unit2", "mode": "recall-only"})
    state = _play(client, ["sak"])
    assert [m["english"] for m in state["missed"]] == ["sack"]
