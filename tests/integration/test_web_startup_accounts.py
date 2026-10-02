"""Start-up behavior of `python -m src.web` with accounts (spec 015,
contracts/accounts-file-format.md "Validation" and "Start-up banner")."""

from pathlib import Path

import pytest
from flask import Flask

from src.web import __main__ as web_main

VALID = """\
accounts:
  - username: weibo
    password: top-secret-1
    display_name: Weibo
  - username: lily
    password: top-secret-2
"""


def _prepare(tmp_path: Path, accounts_text: str | None) -> list[str]:
    vocab_dir = tmp_path / "vocab"
    vocab_dir.mkdir()
    (vocab_dir / "unit1.md").write_text(
        "---\nenglish: receive\nchinese: 收到\n---\n", encoding="utf-8"
    )
    accounts_file = tmp_path / "accounts.yml"
    if accounts_text is not None:
        accounts_file.write_text(accounts_text, encoding="utf-8")
    return [
        "src.web",
        "--vocab-dir",
        str(vocab_dir),
        "--progress-file",
        str(tmp_path / "progress.md"),
        "--accounts-file",
        str(accounts_file),
    ]


@pytest.fixture
def recorded_run(monkeypatch):
    calls: list[dict] = []

    def fake_run(self, *args, **kwargs):
        calls.append({"app": self, **kwargs})

    monkeypatch.setattr(Flask, "run", fake_run)
    return calls


def test_accounts_file_flag_default_and_override():
    parser = web_main.build_arg_parser()
    assert parser.parse_args([]).accounts_file == Path("accounts.yml")
    assert parser.parse_args(["--accounts-file", "x.yml"]).accounts_file == Path("x.yml")


@pytest.mark.parametrize(
    ("accounts_text", "phrase"),
    [
        (None, "accounts.example.yml"),
        (
            (
                "accounts:\n  - username: lily\n    password: top-secret-1\n"
                "  - username: Lily\n    password: top-secret-2\n"
            ),
            "is used more than once",
        ),
        ("accounts: []\n", "defines no accounts"),
    ],
)
def test_invalid_accounts_exit_2_without_starting(
    tmp_path, monkeypatch, capsys, recorded_run, accounts_text, phrase
):
    monkeypatch.setattr("sys.argv", _prepare(tmp_path, accounts_text))
    with pytest.raises(SystemExit) as exc:
        web_main.main()
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert phrase in err
    assert "top-secret" not in err
    assert recorded_run == []


def test_valid_accounts_banner_lists_progress_files_without_passwords(
    tmp_path, monkeypatch, capsys, recorded_run
):
    monkeypatch.setattr("sys.argv", _prepare(tmp_path, VALID))
    web_main.main()
    out = capsys.readouterr().out
    progress = tmp_path / "progress.md"
    assert f"Accounts: weibo → {progress}, lily → {tmp_path / 'progress-lily.md'}" in out
    assert "top-secret" not in out

    client = recorded_run[0]["app"].test_client()
    assert client.get("/api/state").status_code == 401
    resp = client.post("/api/login", json={"username": "weibo", "password": "top-secret-1"})
    assert resp.status_code == 200


def test_server_runs_threaded_so_accounts_never_block_each_other(
    tmp_path, monkeypatch, recorded_run
):
    monkeypatch.setattr("sys.argv", _prepare(tmp_path, VALID))
    web_main.main()
    assert recorded_run[0]["threaded"] is True
