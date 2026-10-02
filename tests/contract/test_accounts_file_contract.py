"""Contract tests for contracts/accounts-file-format.md (spec 015)."""

from pathlib import Path

import pytest

from src.services.accounts import AccountsFileError, load_accounts

EXAMPLE_PATH = Path(__file__).resolve().parents[2] / "accounts.example.yml"


def test_committed_example_file_loads(tmp_path: Path):
    accounts = load_accounts(EXAMPLE_PATH, tmp_path / "progress.md")
    assert [a.username for a in accounts] == ["weibo", "lily"]
    assert accounts[0].progress_file == tmp_path / "progress.md"
    assert accounts[1].progress_file == tmp_path / "progress-lily.md"


@pytest.mark.parametrize(
    ("text", "phrase"),
    [
        (None, "not found"),
        ("accounts: [\n", "is not valid"),
        ("accounts: []\n", "defines no accounts"),
        ("accounts:\n  - username: a\n", "is required"),
        ("accounts:\n  - username: 'a b'\n    password: p\n", "may only use"),
        (
            "accounts:\n  - username: a\n    password: p\n  - username: A\n    password: q\n",
            "is used more than once",
        ),
    ],
)
def test_validation_messages_name_file_and_phrase(tmp_path: Path, text, phrase):
    path = tmp_path / "accounts.yml"
    if text is not None:
        path.write_text(text, encoding="utf-8")
    with pytest.raises(AccountsFileError) as exc:
        load_accounts(path, tmp_path / "progress.md")
    assert "accounts.yml" in str(exc.value)
    assert phrase in str(exc.value)
