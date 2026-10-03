"""Unit tests for the PendingImport / ImportItem model (spec 018,
data-model.md): derived counts and the Import State API shape."""

from src.services.enrichment import ImportItem, PendingImport

OWN = {"source": "own", "list": "unit1", "ipa": None, "chinese": "收到", "alternates": []}
SHARED = {"source": "shared", "list": "t-words", "ipa": None, "chinese": "河", "alternates": []}


def _item(english, state="enriched", **kwargs):
    defaults = {"chinese": "中" if state == "enriched" else None}
    defaults.update(kwargs)
    return ImportItem(english=english, position="line 1", supplied={}, state=state, **defaults)


def _pending(items, skipped=None):
    return PendingImport(
        list_name="z-words",
        source_filename="z-words.txt",
        created_at="2026-10-03T09:15:00+00:00",
        status="partially_failed",
        failure_reason=None,
        upload_skipped=skipped or [],
        items=items,
    )


def test_counts():
    pending = _pending(
        [
            _item("a"),
            _item("b", state="failed", error="x"),
            _item("c", state="waiting"),
            _item("d", state="enriching"),
            _item("a", state="duplicate", duplicate_of=0),
        ]
    )
    assert pending.total == 4
    assert pending.done == 2
    assert pending.enriched_count == 1
    assert pending.failed_count == 1


def test_savable_and_updates():
    keep = _item("receive", existing=OWN, choice="keep")
    update = _item("give", existing=OWN, choice="update")
    shared = _item("river", existing=SHARED)
    plain = _item("zealous")
    failed = _item("tyre", state="failed")
    failed_update = _item("take", state="failed", existing=OWN, choice="update")
    pending = _pending([keep, update, shared, plain, failed, failed_update])

    assert pending.savable == [shared, plain]
    assert pending.updates == [update]


def test_to_api_shape():
    skipped = [f"line {n}: no English word" for n in range(25)]
    pending = _pending([_item("zealous", ipa="ˈzeləs"), _item("tyre", state="failed")], skipped)
    api = pending.to_api()
    assert set(api) == {
        "list_name",
        "source_filename",
        "status",
        "failure_reason",
        "total",
        "done",
        "enriched_count",
        "failed_count",
        "savable_count",
        "upload_skipped",
        "upload_skipped_count",
        "items",
    }
    assert api["savable_count"] == 1
    assert len(api["upload_skipped"]) == 20
    assert api["upload_skipped_count"] == 25
    assert [i["index"] for i in api["items"]] == [0, 1]
    assert set(api["items"][0]) == {
        "index",
        "english",
        "state",
        "ipa",
        "ipa_review",
        "chinese",
        "alternates",
        "dropped_alternates",
        "error",
        "existing",
        "choice",
        "duplicate_of",
    }
    assert api["items"][0]["ipa"] == "ˈzeləs"


def test_json_round_trip_omits_derived():
    pending = _pending([_item("zealous")])
    data = pending.to_json()
    assert "total" not in data
    assert PendingImport.from_json(data) == pending
