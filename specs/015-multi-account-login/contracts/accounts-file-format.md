# Contract: Accounts File (`accounts.yml`)

Read once by `src/services/accounts.py::load_accounts` when the web UI
starts (`python -m src.web`). Path: `--accounts-file`, default
`./accounts.yml`. Gitignored; `accounts.example.yml` is committed as a
template. Covers spec FR-001, FR-003, FR-012, FR-013, FR-015.

## Format

A single YAML document with one top-level key, `accounts`, holding a list:

```yaml
accounts:
  - username: weibo
    password: change-me
    display_name: Weibo
  - username: lily
    password: change-me-too
    display_name: Lily
```

| Key | Required | Rules |
|---|---|---|
| `username` | yes | String. Leading/trailing space and case are ignored (`" Weibo "` → `weibo`). After normalizing it must match `^[a-z0-9_-]{1,32}$` and be unique. |
| `password` | yes | Non-empty string, used exactly as written. Quote it if it could be read as a number or boolean (`"1234"`, `"yes"`); a non-string value is rejected. |
| `display_name` | no | String shown in the web header. Omitted or blank → the username is shown. |

Unknown keys are ignored (room for a future `password_hash`).

## Order matters

The **first** account inherits the existing `--progress-file` (default
`progress.md`). Every other account writes to
`<progress stem>-<username><suffix>` beside it, e.g. `progress-lily.md`.
Reordering the list therefore changes which account owns `progress.md`.

## Validation (start-up fails, exit status 2, message on stderr)

| Condition | Message (shape) |
|---|---|
| File missing | `Accounts file not found: accounts.yml — copy accounts.example.yml to accounts.yml and edit it.` |
| Not valid YAML / top level not a mapping with an `accounts` list | `Accounts file accounts.yml is not valid: <reason>` |
| `accounts` list empty | `Accounts file accounts.yml defines no accounts.` |
| Entry missing `username` or `password`, or `password` empty / not a string | `Account #<n> in accounts.yml: <field> is required.` |
| Invalid username | `Account #<n> in accounts.yml: username "<value>" may only use a–z, 0–9, "_" and "-" (max 32).` |
| Duplicate username (case-insensitive) | `Accounts file accounts.yml: username "<value>" is used more than once.` |

No message, banner, log line, or exception text ever contains a password.

## Start-up banner (on success)

```text
English Tutor web UI running at http://0.0.0.0:8420 (Ctrl+C to stop)
Accounts: weibo → progress.md, lily → progress-lily.md
```
