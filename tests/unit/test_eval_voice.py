"""Unit tests for the voice accuracy tool (spec 022 T022), with a faked
recogniser and fake clips."""

import yaml

from src.services import speech_client
from src.services.speech_client import TranscriptionResult
from src.tools import eval_voice

SENTENCES = {
    "a.webm": "She is zealous about recycling.",
    "b.webm": "The rent is due on Friday.",
}


def _folder(tmp_path, sentences=SENTENCES, clips=("a.webm", "b.webm")):
    (tmp_path / "sentences.yml").write_text(yaml.safe_dump(sentences), encoding="utf-8")
    for name in clips:
        (tmp_path / name).write_bytes(name.encode())
    return tmp_path


def _fake(monkeypatch, heard, available=True):
    monkeypatch.setattr(speech_client, "is_available", lambda: available)
    monkeypatch.setattr(speech_client, "transcribe", lambda audio: heard[audio.decode()])


def test_perfect_run_passes(tmp_path, monkeypatch, capsys):
    _fake(monkeypatch, {n: TranscriptionResult("ok", s) for n, s in SENTENCES.items()})
    assert eval_voice.main([str(_folder(tmp_path))]) == 0
    out = capsys.readouterr().out
    assert "Word accuracy: 11/11 (100%" in out
    assert "PASS" in out


def test_accuracy_counts_sentence_words_marked_same(tmp_path, monkeypatch, capsys):
    heard = {
        "a.webm": TranscriptionResult("ok", "She is jealous about recycling"),  # 4/5
        "b.webm": TranscriptionResult("ok", "The rent is due Friday"),  # 5/6
    }
    _fake(monkeypatch, heard)
    assert eval_voice.main([str(_folder(tmp_path))]) == 1
    out = capsys.readouterr().out
    assert "Word accuracy: 9/11 (82%" in out
    assert "a.webm" in out and "zealous" in out
    assert "FAIL" in out


def test_nothing_heard_counts_as_all_missed(tmp_path, monkeypatch, capsys):
    heard = {
        "a.webm": TranscriptionResult("nothing_heard"),
        "b.webm": TranscriptionResult("ok", SENTENCES["b.webm"]),
    }
    _fake(monkeypatch, heard)
    assert eval_voice.main([str(_folder(tmp_path))]) == 1
    assert "Word accuracy: 6/11" in capsys.readouterr().out


def test_missing_clip_is_reported(tmp_path, monkeypatch, capsys):
    _fake(monkeypatch, {"a.webm": TranscriptionResult("ok", SENTENCES["a.webm"])})
    assert eval_voice.main([str(_folder(tmp_path, clips=("a.webm",)))]) == 1
    assert "MISSING b.webm" in capsys.readouterr().out


def test_slow_clip_fails(tmp_path, monkeypatch, capsys):
    _fake(monkeypatch, {n: TranscriptionResult("ok", s) for n, s in SENTENCES.items()})
    ticks = iter([0.0, 4.0, 10.0, 10.5])
    monkeypatch.setattr(eval_voice.time, "monotonic", lambda: next(ticks))
    assert eval_voice.main([str(_folder(tmp_path))]) == 1
    out = capsys.readouterr().out
    assert "1 over 3 s" in out


def test_unavailable_recogniser(tmp_path, monkeypatch, capsys):
    _fake(monkeypatch, {}, available=False)
    assert eval_voice.main([str(_folder(tmp_path))]) == 2
    assert "voice" in capsys.readouterr().err.lower()


def test_unavailable_during_run(tmp_path, monkeypatch):
    _fake(monkeypatch, {n: TranscriptionResult("unavailable") for n in SENTENCES})
    assert eval_voice.main([str(_folder(tmp_path))]) == 2


def test_model_option(tmp_path, monkeypatch):
    _fake(monkeypatch, {n: TranscriptionResult("ok", s) for n, s in SENTENCES.items()})
    chosen = []
    monkeypatch.setattr(speech_client, "configure", chosen.append)
    eval_voice.main([str(_folder(tmp_path)), "--model", "small"])
    assert chosen == ["small"]


def test_folder_without_sentences_file(tmp_path, monkeypatch, capsys):
    _fake(monkeypatch, {})
    assert eval_voice.main([str(tmp_path)]) == 1
    assert "sentences.yml" in capsys.readouterr().err
