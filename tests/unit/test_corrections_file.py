"""The hidden .corrections.json beside the word files (spec 023,
contracts/corrections-file.md): fingerprints, the overlay, records and
their limits, and tolerant reading."""

import hashlib
import json
import os
import threading

import pytest

from src.services import corrections_file as cf
from src.services.corrections_file import CorrectionRecord, CorrectionsData, WordValues

TAILOR = WordValues.normal("ˈteɪlə", "裁缝；定制", ["n.", "v."])


def _record(**changes) -> CorrectionRecord:
    fields = {
        "id": "a1b2c3d4e5f6",
        "batch": "0f9e8d7c6b5a",
        "file": "T_words.md",
        "group": "t-words",
        "english": "tailor",
        "origin_chinese": "裁缝；定制",
        "field": "chinese",
        "old": "裁缝；定制",
        "new": "裁缝；定做（衣服）",
        "at": "2026-10-21T09:30:00Z",
        "undone_at": None,
    }
    fields.update(changes)
    return CorrectionRecord(**fields)


# --- WordValues and fingerprints -------------------------------------------


def test_values_are_compared_after_normalising():
    assert WordValues.normal("/ˈteɪlə/", "  裁缝；定制 ", ["noun", "verb"]) == TAILOR
    assert WordValues.normal(None, "裁缝", []) != WordValues.normal("ˈteɪlə", "裁缝", [])
    assert TAILOR.to_json() == {"ipa": "ˈteɪlə", "chinese": "裁缝；定制", "pos": ["n.", "v."]}


def test_fingerprint_is_sha256_of_the_six_parts():
    expected = hashlib.sha256(
        "T_words.md|t-words|tailor|ˈteɪlə|裁缝；定制|n. v.".encode()
    ).hexdigest()
    assert cf.fingerprint("T_words.md", "t-words", "tailor", TAILOR) == expected


def test_fingerprint_is_stable_and_ignores_formatting():
    loose = WordValues.normal("/ˈteɪlə/", " 裁缝；定制 ", ["noun", "verb"])
    assert cf.fingerprint("T_words.md", "t-words", "tailor", loose) == cf.fingerprint(
        "T_words.md", "t-words", "tailor", TAILOR
    )


@pytest.mark.parametrize(
    "args",
    [
        ("U_words.md", "t-words", "tailor", TAILOR),
        ("T_words.md", None, "tailor", TAILOR),
        ("T_words.md", "t-words", "Tailor", TAILOR),
        (
            "T_words.md",
            "t-words",
            "tailor",
            WordValues.normal("ˈteɪlər", "裁缝；定制", ["n.", "v."]),
        ),
        ("T_words.md", "t-words", "tailor", WordValues.normal("ˈteɪlə", "裁缝", ["n.", "v."])),
        ("T_words.md", "t-words", "tailor", WordValues.normal("ˈteɪlə", "裁缝；定制", ["n."])),
    ],
)
def test_fingerprint_changes_with_any_part(args):
    assert cf.fingerprint(*args) != cf.fingerprint("T_words.md", "t-words", "tailor", TAILOR)


def test_overlay_key():
    assert (
        cf.overlay_key("T_words.md", "t-words", "tailor", "裁缝")
        == "T_words.md|t-words|tailor|裁缝"
    )
    assert cf.overlay_key("T_words.md", None, "tailor", "裁缝") == "T_words.md||tailor|裁缝"


# --- Records ------------------------------------------------------------------


def test_record_round_trips_and_ids_are_12_hex():
    record = _record(field="pos", old=["v."], new=["n."])
    assert CorrectionRecord.from_json(json.loads(json.dumps(record.to_json()))) == record
    new_id = cf.new_id()
    assert len(new_id) == 12 and int(new_id, 16) >= 0


@pytest.mark.parametrize(
    "broken",
    [
        {"field": "english"},
        {"id": 5},
        {"at": None},
        {"old": 3},
    ],
)
def test_record_with_wrong_types_is_refused(broken):
    data = {**_record().to_json(), **broken}
    with pytest.raises(ValueError):
        CorrectionRecord.from_json(data)


# --- Reading and writing ------------------------------------------------------


def test_missing_file_is_empty(tmp_path):
    data = cf.read(tmp_path)
    assert data.overlay == {} and data.checked == [] and data.records == []


@pytest.mark.parametrize(
    "text",
    [
        "not json",
        "[]",
        json.dumps({"version": 2, "overlay": {}, "checked": ["x"], "records": []}),
    ],
)
def test_unreadable_file_is_empty(tmp_path, text):
    (tmp_path / cf.FILE_NAME).write_text(text, encoding="utf-8")
    data = cf.read(tmp_path)
    assert data.overlay == {} and data.checked == [] and data.records == []


def test_wrong_parts_are_dropped_part_by_part(tmp_path):
    good = _record().to_json()
    bad = {**good, "field": "english"}
    (tmp_path / cf.FILE_NAME).write_text(
        json.dumps(
            {
                "version": 1,
                "overlay": ["not", "an", "object"],
                "checked": ["abc", 5],
                "records": [good, bad, "x"],
            }
        ),
        encoding="utf-8",
    )
    data = cf.read(tmp_path)
    assert data.overlay == {}
    assert data.checked == ["abc"]
    assert data.records == [_record()]


def test_bad_overlay_entries_are_dropped(tmp_path):
    (tmp_path / cf.FILE_NAME).write_text(
        json.dumps(
            {
                "version": 1,
                "overlay": {
                    "a|g|x|y": {"ipa": "ˈteɪlə", "chinese": "裁缝", "pos": ["n."]},
                    "b|g|x|y": {"ipa": "ˈteɪlə", "chinese": "", "pos": ["n."]},
                    "c|g|x|y": "nope",
                },
                "checked": [],
                "records": [],
            }
        ),
        encoding="utf-8",
    )
    assert list(cf.read(tmp_path).overlay) == ["a|g|x|y"]


def test_write_round_trips(tmp_path):
    data = CorrectionsData()
    data.overlay["T_words.md|t-words|tailor|裁缝；定制"] = TAILOR
    data.mark_checked("abc")
    data.add_records([_record()])
    cf.write(tmp_path, data)

    text = (tmp_path / cf.FILE_NAME).read_text(encoding="utf-8")
    assert "裁缝" in text  # not \u-escaped
    raw = json.loads(text)
    assert raw["version"] == 1
    again = cf.read(tmp_path)
    assert again.overlay == data.overlay
    assert again.checked == ["abc"]
    assert again.records == [_record()]


def test_failed_write_keeps_the_old_file(tmp_path, monkeypatch):
    first = CorrectionsData()
    first.mark_checked("old")
    cf.write(tmp_path, first)

    def boom(*args):
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", boom)
    second = CorrectionsData()
    second.mark_checked("new")
    with pytest.raises(OSError):
        cf.write(tmp_path, second)
    assert cf.read(tmp_path).checked == ["old"]
    assert [p.name for p in tmp_path.iterdir()] == [cf.FILE_NAME]


def test_checked_keeps_the_newest_20000(monkeypatch):
    monkeypatch.setattr(cf, "MAX_CHECKED", 3)
    data = CorrectionsData()
    for fp in ["a", "b", "c", "a", "d"]:
        data.mark_checked(fp)
    # Marking a fingerprint twice keeps one copy; the oldest go first.
    assert data.checked == ["b", "c", "d"]
    assert data.is_checked("d") and not data.is_checked("a")


def test_limits_are_as_specified():
    assert cf.MAX_CHECKED == 20_000
    assert cf.MAX_RECORDS == 500


def test_records_are_newest_first_and_capped(monkeypatch):
    monkeypatch.setattr(cf, "MAX_RECORDS", 3)
    data = CorrectionsData()
    data.add_records([_record(id="000000000001")])
    data.add_records([_record(id="000000000002"), _record(id="000000000003")])
    data.add_records([_record(id="000000000004")])
    assert [r.id for r in data.records] == ["000000000004", "000000000002", "000000000003"]


def test_update_serialises_writers(tmp_path):
    def add(n):
        def fn(data):
            data.add_records([_record(id=f"{n:012x}")])

        cf.update(tmp_path, fn)

    threads = [threading.Thread(target=add, args=(n,)) for n in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(cf.read(tmp_path).records) == 20


def test_update_returns_the_functions_result(tmp_path):
    assert cf.update(tmp_path, lambda data: "done") == "done"
