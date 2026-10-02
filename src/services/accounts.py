"""Load learner accounts from accounts.yml and check logins (spec 015,
contracts/accounts-file-format.md). Error messages never include a
password (FR-015)."""

import hmac
import re
from pathlib import Path

import yaml

from src.models.account import Account

USERNAME_RE = re.compile(r"^[a-z0-9_-]{1,32}$")


class AccountsFileError(Exception):
    """Raised when the accounts file is missing or invalid."""


def _progress_file_for(index: int, username: str, progress_file: Path) -> Path:
    """The first account inherits *progress_file*; the rest get a sibling
    `<stem>-<username><suffix>` (research.md R4)."""
    if index == 0:
        return progress_file
    return progress_file.with_name(f"{progress_file.stem}-{username}{progress_file.suffix}")


def load_accounts(path: Path, progress_file: Path) -> list[Account]:
    name = path.name
    if not path.exists():
        raise AccountsFileError(
            f"Accounts file not found: {path} — copy accounts.example.yml to {name} and edit it."
        )

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        # Only the problem and line number: PyYAML's full message quotes the
        # offending source line, which could be a password (FR-015).
        problem = getattr(exc, "problem", None) or "YAML syntax error"
        mark = getattr(exc, "problem_mark", None)
        where = f" (line {mark.line + 1})" if mark is not None else ""
        raise AccountsFileError(f"Accounts file {name} is not valid: {problem}{where}") from None

    if not isinstance(data, dict) or not isinstance(data.get("accounts"), list):
        raise AccountsFileError(
            f"Accounts file {name} is not valid: expected a top-level 'accounts' list"
        )

    entries = data["accounts"]
    if not entries:
        raise AccountsFileError(f"Accounts file {name} defines no accounts.")

    accounts: list[Account] = []
    seen: set[str] = set()
    for index, entry in enumerate(entries):
        number = index + 1
        if not isinstance(entry, dict) or not isinstance(entry.get("username"), str):
            raise AccountsFileError(f"Account #{number} in {name}: username is required.")
        password = entry.get("password")
        if not isinstance(password, str) or password == "":
            raise AccountsFileError(f"Account #{number} in {name}: password is required.")

        username = entry["username"].strip().lower()
        if not USERNAME_RE.match(username):
            raise AccountsFileError(
                f'Account #{number} in {name}: username "{username}" may only use '
                'a–z, 0–9, "_" and "-" (max 32).'
            )
        if username in seen:
            raise AccountsFileError(
                f'Accounts file {name}: username "{username}" is used more than once.'
            )
        seen.add(username)

        display_name = entry.get("display_name")
        if isinstance(display_name, str):
            display_name = display_name.strip() or None
        else:
            display_name = None

        accounts.append(
            Account(
                username=username,
                password=password,
                display_name=display_name,
                progress_file=_progress_file_for(index, username, progress_file),
            )
        )

    return accounts


def authenticate(accounts: list[Account], username: str, password: str) -> Account | None:
    """Return the account matching *username* (trimmed, case-insensitive)
    and *password* (exact), or None."""
    wanted = username.strip().lower()
    for account in accounts:
        if account.username == wanted:
            if hmac.compare_digest(password.encode("utf-8"), account.password.encode("utf-8")):
                return account
            return None
    return None
