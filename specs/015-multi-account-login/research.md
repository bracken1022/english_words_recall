# Research: Multiple Learner Accounts with Simple Login

All Technical Context items were resolvable from the existing codebase
(Python 3.11+, Flask ≥3.0, PyYAML, pytest; one Flask process holding one
shared `PracticeSession`). No new dependencies are needed. Each decision
below records what was chosen, why, and what was rejected.

## R1. Where the "hardcoded" accounts live

- **Decision**: A small YAML file, `accounts.yml`, read once at web start-up
  (path overridable with `--accounts-file`, default `./accounts.yml`).
  `accounts.yml` is gitignored like `progress.md`; a committed
  `accounts.example.yml` shows the format. Format:
  `contracts/accounts-file-format.md`.
- **Rationale**: Matches the user's "hardcoded credentials, no
  verification": the operator writes the list by hand, nothing in the app
  creates or edits accounts, and changes take effect on restart. Keeping it
  out of source code stops a family member's password from being committed
  to git (Constitution III: access limited to what the feature needs). A single YAML
  document reuses the PyYAML dependency already used
  for vocabulary and progress files.
- **Alternatives considered**:
  - *A Python constant in `src/web/accounts.py`* — literally "hardcoded",
    but puts passwords into version control and requires a code edit to
    change one. Rejected.
  - *Environment variables* — awkward for a list of accounts with display
    names; easy to leak in shell history. Rejected.
  - *A database / sign-up screen* — out of scope (spec FR-001).

## R2. How a browser stays logged in

- **Decision**: Flask's built-in signed-cookie `session` stores only a
  random login id (`secrets.token_urlsafe(32)`); the server keeps an
  in-memory map of live login ids → usernames, and logout deletes the id so
  a saved copy of the old cookie stops working (found during quickstart
  validation: a stateless username cookie stayed valid after logout if
  replayed). `SECRET_KEY` is generated fresh at each start-up with
  `secrets.token_hex(32)`. The session is marked permanent with a long
  lifetime (365 days) so it survives browser restarts (FR-010).
  `SESSION_COOKIE_HTTPONLY=True` (Flask default) and `SAMESITE="Lax"`.
- **Rationale**: Zero new dependencies; the cookie is tamper-proof so a
  learner can't edit it to become another account. A per-start-up random
  key means restarting the tutor logs everyone out, which the spec
  explicitly accepts and which avoids storing a secret on disk.
- **Alternatives considered**:
  - *Server-side token table* — more code for no benefit at this scale.
  - *Persisting `SECRET_KEY` to disk so logins survive restarts* — not
    required; adds a secret file to manage. Rejected for now.
  - *Flask-Login* — a new dependency for what is ~30 lines here. Rejected.

## R3. Per-account practice session state

- **Decision**: Replace the single `app.practice_session` with a registry
  `{username: PracticeSession}` guarded by a `threading.Lock`. An account's
  `PracticeSession` is created lazily on its first authenticated request,
  with the same `vocab_dir`, `group`, `offer_choice`, `order`, `mode` the
  single session gets today, and that account's own `progress_file`.
  `PracticeSession` itself is unchanged.
- **Rationale**: `PracticeSession` already encapsulates everything
  per-learner (collection, order, mode, index, score, pending attempt,
  review-in-progress flag), so one instance per account gives FR-007
  isolation with no changes to grading, review, or persistence logic.
  Flask's dev server is threaded by default, so a slow Ollama review for
  one account doesn't block the other. Two devices on the *same* account
  share one instance, which is exactly today's one-learner-two-tabs
  behavior (spec edge case).
- **Alternatives considered**:
  - *One `PracticeSession` per browser cookie* — would split one learner
    into several sessions across devices and complicate FR-009. Rejected.
  - *Eager creation for every account at start-up* — works, but loads
    vocabulary for accounts that may never log in this run. Lazy is just as
    simple. Either is acceptable; lazy chosen.

## R4. Per-account progress history file

- **Decision**: The **first** account in `accounts.yml` uses
  `--progress-file` exactly as today (default `./progress.md`), so it
  inherits all existing history (FR-012). Every other account uses a
  sibling file named `<stem>-<username><suffix>` in the same directory,
  e.g. `progress-lily.md`. Usernames are restricted to
  `[a-z0-9_-]{1,32}` so they are always filename-safe. The file format
  (`specs/001-vocab-recall-tutor/contracts/progress-log-format.md`) is
  unchanged.
- **Rationale**: No migration step, no rewrite of the existing log, and
  every history remains one plain human-readable Markdown file. Keeping
  the files side by side makes them easy for the operator to find and back
  up.
- **Alternatives considered**:
  - *One shared file with an `account:` field per attempt* — would require
    changing the progress-log contract and filtering on read; a bug would
    leak one learner's history into another's. Rejected.
  - *A per-account `progress_file` key in `accounts.yml`* — more flexible
    but nobody asked for it. Rejected (YAGNI); can be added later without
    breaking the format.
  - *Moving files into a `progress/` directory* — would orphan the existing
    `progress.md` or need a migration. Rejected.

## R5. Enforcing login on the API

- **Decision**: A `before_request` hook rejects every `/api/*` request
  except `POST /api/login` with `401 {"error": "login required"}` when the
  cookie has no username, or names a username not in the current account
  list. The HTML page (`GET /`) and static files are always served; the
  front end shows the login screen whenever `GET /api/state` returns 401.
  `POST /api/transcribe` is also protected (it's a practice action and
  consumes local CPU).
- **Rationale**: One guard covers every existing and future endpoint, so
  FR-011 can't be missed by a new route. 401 without any state change
  satisfies SC-004.
- **Alternatives considered**: a decorator on each route — easy to forget
  on a new route. Rejected.

## R6. Password checking

- **Decision**: Plain-text passwords in `accounts.yml`, compared with
  `hmac.compare_digest` after encoding both to UTF-8. Username is
  normalized with `.strip().lower()`; password is compared exactly. A wrong
  username and a wrong password produce the identical 401 body.
- **Rationale**: The spec's trusted-household assumption means hashing adds
  operator friction (they'd need a tool to produce hashes) with no real
  threat model behind it. `compare_digest` costs nothing and avoids an
  obvious timing difference.
- **Alternatives considered**: bcrypt/argon2 hashes — a new dependency and
  a hash-generation step for the operator. Deferred; the file format leaves
  room for a `password_hash` key later.

## R7. Logout semantics

- **Decision**: `POST /api/logout` clears the cookie session **and**
  replaces that account's `PracticeSession` in the registry with a fresh
  one. This discards any word in progress without recording it (FR-009)
  and means the account starts clean at its next login.
- **Rationale**: The simplest way to guarantee nothing half-finished is
  logged or left behind. A second device still logged in to the same
  account will see the fresh session on its next poll — acceptable and
  consistent with the "End session" behavior.
- **Alternatives considered**: calling `PracticeSession.end_session()` —
  it refuses when the group is locked at start-up or when the step is
  `complete`/`choose`, so it can't be used unconditionally. Rejected.

## R8. Backward compatibility of `create_app` and the CLI

- **Decision**: `create_app` gains an `accounts: list[Account] | None =
  None` parameter. `src/web/__main__.py` always loads and passes accounts,
  so the shipped web UI always requires login. When a caller passes
  `None` (only the existing test suite does), the app keeps today's
  single-shared-session, no-login behavior, so the existing web tests need
  no rewrite. The command-line tutor (`src/cli`) is not touched (FR-014).
- **Rationale**: Keeps this feature's diff small and focused, and keeps the
  existing contract tests proving that the practice flow itself is
  unchanged.
- **Alternatives considered**: making `accounts` mandatory and updating
  every existing web test to log in first — larger churn for no behavior
  gain. Rejected; new tests cover the accounts-enabled path.

## R9. Start-up validation

- **Decision**: `load_accounts(path)` raises `AccountsFileError` with a
  human-readable message, and `src/web/__main__.py` prints it to stderr and
  exits with status 2, when: the file is missing (message points to
  `accounts.example.yml`), not valid YAML, has no accounts, an entry lacks
  `username` or `password`, a username is invalid or duplicated
  (case-insensitive), or a password is empty. Messages name the offending
  username/entry number but never print a password (FR-013, FR-015). The
  start-up banner lists account usernames and their progress files.
- **Rationale**: Fail fast with a clear fix, rather than a server nobody
  can log in to.
