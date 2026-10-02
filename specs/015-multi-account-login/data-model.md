# Data Model: Multiple Learner Accounts with Simple Login

## Account (new — `src/models/account.py`)

An operator-defined learner who can log in to the web UI. Immutable for the
life of the server process.

| Field | Type | Rules |
|---|---|---|
| `username` | str | Required. Stored normalized (`strip().lower()`). Must match `^[a-z0-9_-]{1,32}$`. Unique across all accounts. |
| `password` | str | Required, non-empty. Compared exactly (no trimming). Never logged, printed, rendered, or included in `repr`. |
| `display_name` | str \| None | Optional. Shown in the header; falls back to `username`. Trimmed; empty → `None`. |
| `progress_file` | Path | Derived, not read from the file (see below). |

**Derived `progress_file`** (research R4), given `--progress-file` = `P`:

- the first account in file order → `P` (inherits existing history);
- any other account → `P.with_name(f"{P.stem}-{username}{P.suffix}")`,
  e.g. `progress.md` → `progress-lily.md`.

**Display label** = `display_name or username`.

Source: `accounts.yml` — see `contracts/accounts-file-format.md`. Loaded by
`load_accounts(path, progress_file) -> list[Account]` in
`src/services/accounts.py`, which raises `AccountsFileError` on any
validation failure (research R9).

## Login (device session — Flask signed cookie)

| Key | Type | Meaning |
|---|---|---|
| `session["login_id"]` | str | Random id issued at login. The server's in-memory `active_logins: dict[login_id, username]` maps it to an account; logout deletes the entry. |

- Created by a successful `POST /api/login`; cleared by `POST /api/logout`.
- Valid only while (a) the server process that issued it is running (the
  `SECRET_KEY` and `active_logins` are per-process), (b) its `login_id` is
  still in `active_logins` (not logged out), and (c) that username still
  exists in the loaded account list.
- Marked permanent, 365-day lifetime → survives browser restarts.

### Login state transitions

```text
            POST /api/login (valid)
 logged-out ───────────────────────────▶ logged-in(username)
     ▲   ▲                                   │
     │   └── POST /api/login (invalid) ──┐   │ POST /api/logout
     │       stays logged-out ◀──────────┘   │ server restart
     └───────────────────────────────────────┘ login id unknown
```

A `POST /api/login` while already logged in replaces the login (switching
accounts) — the previous account's `PracticeSession` is left untouched.

## SessionRegistry (new — `src/web/session_registry.py`)

Maps each account to its own `PracticeSession`.

| Member | Meaning |
|---|---|
| `_sessions: dict[str, PracticeSession]` | One entry per account that has made an authenticated request since start-up (or since its last logout). |
| `_lock: threading.Lock` | Guards creation/replacement only. |
| `get(account) -> PracticeSession` | Returns the account's session, creating it on first use with that account's `progress_file` and the server-wide `vocab_dir`, `group`, `offer_choice`, `order`, `mode`. |
| `reset(account) -> None` | Replaces the account's session with a fresh one (logout, research R7). The word in progress is discarded unrecorded. |

## PracticeSession (existing — unchanged)

`src/web/session_state.py`. No fields or transitions change. The only
difference is ownership: there is now one instance per account (via
`SessionRegistry`) instead of one per server, and each is constructed with
its own account's `progress_file`.

## PracticeAttempt / progress log (existing — unchanged)

Same fields and file format
(`specs/001-vocab-recall-tutor/contracts/progress-log-format.md`). No
`account` field is added: which account an attempt belongs to is given by
which file it's in.

## Relationships

```text
accounts.yml ──loads──▶ Account (1..N)
Account 1 ──── 0..1 PracticeSession  (via SessionRegistry, lazily)
Account 1 ──── 1 progress history file
Browser cookie 0..1 ──▶ Account       (many browsers may share one Account)
Vocabulary dir 1 ──── shared by all PracticeSessions
```
