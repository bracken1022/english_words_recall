"""Unit tests for src/web/session_registry.py (spec 015, data-model.md
"SessionRegistry")."""

from pathlib import Path

from src.models.account import Account
from src.web.session_registry import SessionRegistry

VOCAB = (
    "---\nenglish: receive\nchinese: 收到\ngroup: unit1\n---\n\n"
    "---\nenglish: accept\nchinese: 接受\ngroup: unit2\n---\n"
)


def _setup(tmp_path: Path, **kwargs):
    vocab_dir = tmp_path / "vocab"
    vocab_dir.mkdir()
    (vocab_dir / "unit1.md").write_text(VOCAB, encoding="utf-8")
    options = {"group": None, "offer_choice": True, "order": "sequential", "mode": "sentence"}
    options.update(kwargs)
    registry = SessionRegistry(vocab_dir=vocab_dir, **options)
    a = Account("weibo", "pw-a", "Weibo", tmp_path / "progress.md")
    b = Account("lily", "pw-b", None, tmp_path / "progress-lily.md")
    return registry, a, b


def test_get_creates_session_with_account_progress_file(tmp_path: Path):
    registry, a, _ = _setup(tmp_path)
    session = registry.get(a)
    assert session.progress_file == a.progress_file
    assert session.step == "choose"


def test_get_returns_same_session_per_account_and_distinct_across_accounts(tmp_path: Path):
    registry, a, b = _setup(tmp_path)
    assert registry.get(a) is registry.get(a)
    assert registry.get(a) is not registry.get(b)


def test_sessions_are_isolated(tmp_path: Path):
    registry, a, b = _setup(tmp_path)
    registry.get(a).select_collection(None)
    assert registry.get(a).step == "recall"
    assert registry.get(b).step == "choose"


def test_reset_replaces_only_that_account(tmp_path: Path):
    registry, a, b = _setup(tmp_path)
    old_a = registry.get(a)
    old_a.select_collection(None)
    b_session = registry.get(b)
    registry.reset(a)
    assert registry.get(a) is not old_a
    assert registry.get(a).step == "choose"
    assert registry.get(b) is b_session


def test_reset_unknown_account_does_not_raise(tmp_path: Path):
    registry, a, _ = _setup(tmp_path)
    registry.reset(a)
    assert registry.get(a).step == "choose"


def test_startup_options_apply_to_every_session(tmp_path: Path):
    registry, a, _ = _setup(tmp_path, group="unit1", offer_choice=False, mode="recall-only")
    session = registry.get(a)
    assert session.group_locked is True
    assert session.recall_only is True
    assert session.step == "recall"
