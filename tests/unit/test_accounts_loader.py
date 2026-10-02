"""Unit tests for src/services/accounts.py (spec 015, data-model.md
"Account" and contracts/accounts-file-format.md)."""

from pathlib import Path

import pytest

from src.models.account import Account
from src.services.accounts import AccountsFileError, authenticate, load_accounts

VALID = """\
accounts:
  - username: " Weibo "
    password: s3cret-pw
    display_name: Weibo
  - username: lily
    password: lily-pw
"""


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "accounts.yml"
    path.write_text(text, encoding="utf-8")
    return path


def _load(tmp_path: Path, text: str) -> list[Account]:
    return load_accounts(_write(tmp_path, text), tmp_path / "progress.md")


def test_valid_file_loads_in_order_and_normalizes(tmp_path: Path):
    accounts = _load(tmp_path, VALID)
    assert [a.username for a in accounts] == ["weibo", "lily"]
    assert accounts[0].display_name == "Weibo"
    assert accounts[1].display_name is None
    assert accounts[0].password == "s3cret-pw"


def test_blank_display_name_becomes_none(tmp_path: Path):
    accounts = _load(
        tmp_path, 'accounts:\n  - username: a\n    password: p\n    display_name: "  "\n'
    )
    assert accounts[0].display_name is None
    assert accounts[0].label == "a"


def test_label_prefers_display_name(tmp_path: Path):
    assert _load(tmp_path, VALID)[0].label == "Weibo"


def test_progress_files_first_account_inherits_others_get_suffix(tmp_path: Path):
    accounts = _load(tmp_path, VALID)
    assert accounts[0].progress_file == tmp_path / "progress.md"
    assert accounts[1].progress_file == tmp_path / "progress-lily.md"


def test_unknown_keys_are_ignored(tmp_path: Path):
    accounts = _load(
        tmp_path, "accounts:\n  - username: a\n    password: p\n    password_hash: x\n"
    )
    assert accounts[0].username == "a"


def test_repr_and_str_never_contain_password(tmp_path: Path):
    account = _load(tmp_path, VALID)[0]
    assert "s3cret-pw" not in repr(account)
    assert "s3cret-pw" not in str(account)


def test_missing_file_points_to_example(tmp_path: Path):
    with pytest.raises(AccountsFileError) as exc:
        load_accounts(tmp_path / "accounts.yml", tmp_path / "progress.md")
    assert "accounts.example.yml" in str(exc.value)
    assert "not found" in str(exc.value)


@pytest.mark.parametrize(
    "text",
    [
        "accounts: [unclosed\n",
        "- just\n- a list\n",
        "something_else: 1\n",
        "accounts: notalist\n",
        "",
    ],
)
def test_invalid_structure(tmp_path: Path, text: str):
    with pytest.raises(AccountsFileError) as exc:
        _load(tmp_path, text)
    assert "is not valid" in str(exc.value)


def test_empty_list(tmp_path: Path):
    with pytest.raises(AccountsFileError) as exc:
        _load(tmp_path, "accounts: []\n")
    assert "defines no accounts" in str(exc.value)


@pytest.mark.parametrize(
    ("text", "field"),
    [
        ("accounts:\n  - password: secret-x\n", "username"),
        ("accounts:\n  - username: a\n", "password"),
        ('accounts:\n  - username: a\n    password: ""\n', "password"),
        ("accounts:\n  - username: a\n    password: 1234\n", "password"),
        ("accounts:\n  - username: a\n    password: yes\n", "password"),
        ("accounts:\n  - just-a-string\n", "username"),
    ],
)
def test_required_fields(tmp_path: Path, text: str, field: str):
    with pytest.raises(AccountsFileError) as exc:
        _load(tmp_path, text)
    message = str(exc.value)
    assert "Account #1" in message
    assert field in message
    assert "is required" in message
    assert "secret-x" not in message
    assert "1234" not in message


def test_entry_number_is_one_based(tmp_path: Path):
    with pytest.raises(AccountsFileError) as exc:
        _load(tmp_path, "accounts:\n  - username: a\n    password: p\n  - username: b\n")
    assert "Account #2" in str(exc.value)


@pytest.mark.parametrize("username", ["we ibo", "李", "a" * 33, "a.b"])
def test_invalid_username(tmp_path: Path, username: str):
    with pytest.raises(AccountsFileError) as exc:
        _load(tmp_path, f'accounts:\n  - username: "{username}"\n    password: top-pw\n')
    message = str(exc.value)
    assert "may only use" in message
    assert "top-pw" not in message


def test_duplicate_username_ignoring_case(tmp_path: Path):
    with pytest.raises(AccountsFileError) as exc:
        _load(
            tmp_path,
            "accounts:\n  - username: Lily\n    password: pw-one\n"
            "  - username: lily\n    password: pw-two\n",
        )
    message = str(exc.value)
    assert "lily" in message
    assert "is used more than once" in message
    assert "pw-one" not in message and "pw-two" not in message


def test_authenticate_matches_normalized_username_and_exact_password(tmp_path: Path):
    accounts = _load(tmp_path, VALID)
    assert authenticate(accounts, " WEIBO ", "s3cret-pw") is accounts[0]


@pytest.mark.parametrize(
    ("username", "password"),
    [
        ("weibo", "wrong"),
        ("nobody", "s3cret-pw"),
        ("weibo", "s3cret-pw "),
        ("weibo", "S3CRET-PW"),
    ],
)
def test_authenticate_rejects(tmp_path: Path, username: str, password: str):
    assert authenticate(_load(tmp_path, VALID), username, password) is None


def test_yaml_syntax_error_message_does_not_quote_password_line(tmp_path: Path):
    with pytest.raises(AccountsFileError) as exc:
        _load(tmp_path, "accounts:\n  - username: a\n    password: [hidden-pw\n")
    assert "is not valid" in str(exc.value)
    assert "hidden-pw" not in str(exc.value)
