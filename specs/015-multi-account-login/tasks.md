---

description: "Task list for 015-multi-account-login"
---

# Tasks: Multiple Learner Accounts with Simple Login

**Input**: Design documents from `/specs/015-multi-account-login/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md (all present)

**Tests**: Included and REQUIRED. Constitution Principle I (Test-First Development, NON-NEGOTIABLE) requires tests before implementation, which overrides the "tests optional" default. Every test task must be written and **seen failing for the right reason** before its implementation task starts.

**Organization**: Tasks are grouped by user story (spec.md: US1 P1 log in + separate histories, US2 P2 practice at the same time, US3 P3 log out / stay logged in) so each story can be built and checked on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no unmet dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Every task includes an exact file path

## Path Conventions

Single project, same layout as `001`–`014`. New code goes in `src/models/account.py`, `src/services/accounts.py`, `src/web/session_registry.py`. Existing files touched: `src/web/app.py`, `src/web/__main__.py`, `src/web/templates/index.html`, `src/web/static/app.js`, `src/web/static/style.css`, `.gitignore`, `README.md`. **Not touched**: `src/web/session_state.py`, anything under `src/cli/`, `src/services/{matcher,llm_client,progress_log,vocabulary_loader,speech_client}.py`, and every existing test file except `tests/unit/test_web_static_assets.py`, which only gets new tests added.

Test helpers: build apps the way `tests/contract/test_web_api_contract.py::_make_client` does (tmp `vocab/unit1.md`, `progress_file=tmp_path / "progress.md"`), and pass `accounts=load_accounts(...)` or a list of `Account` objects. Flask's `app.test_client()` keeps cookies per client, so **one test client = one browser/device**; use two clients for two devices.

---

## Phase 1: Setup

**Purpose**: Accounts template and ignore rules, with no new dependencies (Flask and PyYAML are already in `pyproject.toml`).

- [X] T001 [P] Create `accounts.example.yml` at the repo root exactly as in `contracts/accounts-file-format.md` § Format: top-level `accounts:` list with two entries, `username: weibo` / `password: change-me` / `display_name: Weibo` and `username: lily` / `password: change-me-too` / `display_name: Lily`. Add a leading YAML comment: copy this file to `accounts.yml`; the first account owns the existing `progress.md`; others write `progress-<username>.md`; quote passwords that look like numbers or yes/no.
- [X] T002 [P] In `.gitignore`, under the existing "# Local runtime data" block (which already has `/vocabulary/` and `/progress.md`), add `/accounts.yml` and `/progress-*.md`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The `Account` model, the accounts-file loader, and the per-account `SessionRegistry`. Every user story depends on these.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### Tests for Foundational (write first, confirm they FAIL)

- [X] T003 [P] Create `tests/unit/test_accounts_loader.py` covering `load_accounts(path: Path, progress_file: Path) -> list[Account]` and `authenticate(accounts, username, password) -> Account | None` from `src/services/accounts.py`, per `data-model.md` § Account and `contracts/accounts-file-format.md`:
  - a valid two-account file loads in file order, with `display_name` set or `None`;
  - normalization: username `" Weibo "` is stored as `"weibo"`; `display_name: "  "` becomes `None`;
  - `progress_file` derivation with `progress_file=tmp_path / "progress.md"`: the first account gets exactly `tmp_path / "progress.md"`, and the second (`lily`) gets `tmp_path / "progress-lily.md"`, built as `P.with_name(f"{P.stem}-{username}{P.suffix}")`;
  - each of these raises `AccountsFileError`, with the message shape from the contract's Validation table: file missing (message contains `accounts.example.yml`); invalid YAML; top level not a mapping, or `accounts` missing or not a list; empty list; entry missing `username`; entry missing `password`; `password: ""`; non-string password (`password: 1234` unquoted, and `password: yes`); username failing `^[a-z0-9_-]{1,32}$` after normalizing (e.g. `"we ibo"`, `"李"`, 33 chars); duplicate usernames differing only in case (`Lily` and `lily`). Messages that refer to an entry use `Account #<n>` (1-based);
  - for every error case that involves a password, assert the password string is **not** in `str(exc)`;
  - `repr(account)` and `str(account)` do not contain the password;
  - unknown keys (e.g. `password_hash: x`) are ignored;
  - `authenticate`: matches with username `" WEIBO "` and the exact password; returns `None` for the wrong password, an unknown username, a password with extra trailing space, and password case changed.
- [X] T004 [P] Create `tests/unit/test_session_registry.py` for `SessionRegistry` in `src/web/session_registry.py`, per `data-model.md` § SessionRegistry. Construct it with `vocab_dir`, `group=None`, `offer_choice=True`, `order="sequential"`, `mode="sentence"`, and use two `Account`s with different `progress_file`s:
  - `get(a)` returns a `PracticeSession` whose `progress_file == a.progress_file` and `step == "choose"`;
  - calling `get(a)` twice returns the same object, and `get(b)` returns a different one;
  - after `get(a).select_collection(None)`, `get(b).step` is still `"choose"`;
  - `reset(a)` makes `get(a)` return a new object back at `"choose"`, while `get(b)` is the same object as before;
  - `reset` on an account never fetched does not raise;
  - with `group="unit1", offer_choice=False, mode="recall-only"`, `get(a)` is group-locked (`group_locked is True`, `recall_only is True`).
- [X] T005 [P] Create `tests/contract/test_accounts_file_contract.py`:
  - the committed `accounts.example.yml` loads with `load_accounts` into two accounts, `weibo` then `lily`;
  - each row of the contract's Validation table produces a message that includes the file name and the documented key phrase (`not found`, `is not valid`, `defines no accounts`, `is required`, `may only use`, `is used more than once`).

### Implementation for Foundational

- [X] T006 [P] Create `src/models/account.py`: a frozen `@dataclass` `Account` with fields `username: str`, `password: str = field(repr=False)`, `display_name: str | None`, `progress_file: Path`. Add a `label` property returning `display_name or username`, and a module docstring citing spec 015 `data-model.md`. Override `__str__` only if needed so that the password never appears. Depends on T003 failing.
- [X] T007 Create `src/services/accounts.py`:
  - `class AccountsFileError(Exception)`;
  - `USERNAME_RE = re.compile(r"^[a-z0-9_-]{1,32}$")`;
  - `load_accounts(path: Path, progress_file: Path) -> list[Account]`: read with `yaml.safe_load`; validate in the order of the contract table; normalize the username with `.strip().lower()`; require the password to be a non-empty `str` and never strip it; set `display_name` to the stripped value or `None` when blank; derive `progress_file` as the first account → `progress_file`, others → `progress_file.with_name(f"{progress_file.stem}-{username}{progress_file.suffix}")`; raise `AccountsFileError` with the documented messages, which never include a password;
  - `authenticate(accounts, username, password) -> Account | None`: normalize the username, find the account, and compare passwords with `hmac.compare_digest(given.encode("utf-8"), stored.encode("utf-8"))`.

  Module docstring cites `contracts/accounts-file-format.md`. Depends on T006; makes T003 and T005 pass.
- [X] T008 [P] Create `src/web/session_registry.py`: `class SessionRegistry` with `__init__(self, vocab_dir, group, offer_choice, order, mode)`, a private `_sessions: dict[str, PracticeSession]`, and `_lock = threading.Lock()`:
  - `get(account)` creates on first use, under the lock, a `PracticeSession(vocab_dir=..., progress_file=account.progress_file, group=..., offer_choice=..., order=..., mode=...)` keyed by `account.username`;
  - `reset(account)` replaces that entry with a fresh session, under the lock.

  `PracticeSession` itself is not modified. Depends on T006; makes T004 pass.

**Checkpoint**: `pytest tests/unit/test_accounts_loader.py tests/unit/test_session_registry.py tests/contract/test_accounts_file_contract.py` passes. No web behavior has changed yet.

---

## Phase 3: User Story 1 - Log in as yourself and practice with your own history (Priority: P1) 🎯 MVP

**Goal**: The web UI requires a login. A valid username and password lead into the normal practice screens with the account name in the header, every `/api/*` call without a login is refused with 401, and each account's attempts go only to its own progress file. The first account keeps the existing `progress.md`.

**Independent Test**: With two accounts configured, log in as A and practice, then log in as B (a second test client is enough before US3's logout exists) and practice. A's file holds only A's attempts and B's file holds only B's. A call without a login gets 401 and changes no file.

### Tests for User Story 1 (write first, confirm they FAIL)

- [X] T009 [P] [US1] Create `tests/contract/test_web_auth_contract.py` per `contracts/web-auth-api-contract.md`. Build the app with `create_app(..., offer_choice=True, accounts=[weibo, lily])`, where weibo's `progress_file` is `tmp_path/"progress.md"` and lily's is `tmp_path/"progress-lily.md"`.
  - **Login responses:**
    - `POST /api/login {"username":"Weibo ","password":"change-me"}` returns `200` with `{"account":{"username":"weibo","display_name":"Weibo"}}`, and the body does not contain `change-me`;
    - the wrong password and an unknown username each return `401` with the **identical** body `{"error":"Username or password is incorrect"}`;
    - a missing field, a non-string field, `"username":"  "` and `"password":""` each return `400` with `{"error":"Enter both a username and a password"}`;
    - after a failed login, `GET /api/state` is still `401`.
  - **Guard, parametrized over every route:** `GET /api/state` and `POST` to `/api/answer`, `/api/sentence`, `/api/select`, `/api/skip`, `/api/restart`, `/api/end`, `/api/retry-sentence`, `/api/continue`, `/api/transcribe` and `/api/logout`, each without login → `401` with `{"error":"login required"}`, and neither progress file exists afterwards.
  - **Guard, extra cases:** `GET /` → `200` without login. A client whose cookie names a username not in the list → `401`; produce it with `client.session_transaction()` setting `sess["username"] = "ghost"`.
  - **Logged-in state:** after login, `GET /api/state` → `200`, with `step == "choose"` and `account == {"username":"weibo","display_name":"Weibo"}`. An account without `display_name` gets `"display_name": null`.
  - **Legacy mode:** `create_app(...)` with no `accounts` still answers `GET /api/state` with `200` and no login (research R8 regression guard).
- [X] T010 [P] [US1] Create `tests/integration/test_multi_account_flow.py` covering separate histories. Use a vocab file with `receive/收到` and `give up/放弃`, `offer_choice=True`, and accounts weibo (first) and lily.
  - **Separate histories:**
    - pre-write `tmp_path/"progress.md"` with one existing attempt block in the `progress_log` format (use `append_attempt`);
    - client A logs in as weibo, `POST /api/select {"collection":null,"mode":"recall-only"}`, answers `receive`, then `POST /api/continue`;
    - client B logs in as lily, selects the same way, answers `wrong`, then `POST /api/continue`;
    - with `read_attempts`, `progress.md` holds the pre-existing attempt plus weibo's single new attempt; `progress-lily.md` holds exactly lily's one attempt (`answer == "wrong"`); and neither file contains the other account's answer.
  - **Pre-existing history:** when `progress.md` already has attempts and lily logs in and practices, `progress.md`'s contents are byte-for-byte unchanged (FR-012, SC-005).
- [X] T011 [P] [US1] Create `tests/integration/test_web_startup_accounts.py` for `src/web/__main__.py`:
  - `build_arg_parser().parse_args([])` gives `accounts_file == Path("accounts.yml")`, and `--accounts-file x.yml` is honored;
  - **error exits:** call `main()` with `sys.argv` patched (`monkeypatch.setattr("sys.argv", [...])`) and `--accounts-file` pointing to (a) a missing file, (b) a file with a duplicate username, (c) a file with an empty list. Each raises `SystemExit` with code `2`, stderr (`capsys`) contains the documented message, and stderr does not contain any password from the file. Monkeypatch `Flask.run` so it would fail the test if reached;
  - **success:** with a valid file and `Flask.run` monkeypatched to record its kwargs, stdout contains `Accounts: weibo → progress.md, lily → progress-lily.md` (paths shown as given relative to `--progress-file`), stdout contains no password, and `create_app` received `accounts` (assert via the app passed to the recorded run, or by monkeypatching `src.web.__main__.create_app` to capture its kwargs).
- [X] T012 [P] [US1] In `tests/unit/test_web_static_assets.py`, add tests in the existing string-assertion style, per `contracts/login-ui-contract.md`:
  - `index.html` has a `<section id="login-view" class="screen"` containing `id="login-username"` with `autocomplete="username"`, `id="login-password"` with `type="password"` and `autocomplete="current-password"`, a `<label for="login-username"`, a `<label for="login-password"`, a submit button whose text is `Log in`, and `id="login-error"` with `role="alert"`;
  - the header (`<header ... site-header`) contains `id="account-name"` and `id="logout-button"`;
  - `app.js` references `401`, `/api/login`, `login-view`, and the strings `Username or password is incorrect` and `Enter both a username and a password`;
  - `app.js` never references `localStorage` together with the password; simplest form: `"localStorage" not in js`.

### Implementation for User Story 1

- [X] T013 [US1] In `src/web/app.py`, update `create_app` and the routes. Depends on T007, T008; makes T009 and T010 pass.
  - **Import:** `from flask import session as login_session`. The existing local name `session` is the `PracticeSession`, so the Flask import needs a different name.
  - **Signature:** add the parameter `accounts: list[Account] | None = None`.
  - **Legacy branch** (`accounts is None`): keep exactly today's single shared `PracticeSession` stored on `app.practice_session`, with no guard.
  - **Accounts branch:**
    - set `app.secret_key = secrets.token_hex(32)`, `app.config["SESSION_COOKIE_SAMESITE"] = "Lax"`, and `app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=365)`;
    - build `accounts_by_name = {a.username: a for a in accounts}` and store `app.session_registry = SessionRegistry(vocab_dir, group, offer_choice, order, mode)`;
    - add a `@app.before_request` guard: if `request.path.startswith("/api/")` and the path is not `/api/login` and `login_session.get("username")` is not in `accounts_by_name`, return `jsonify({"error": "login required"}), 401`.
  - **Helper:** add a private `_current_session()` that returns `app.practice_session` in legacy mode, otherwise `app.session_registry.get(accounts_by_name[login_session["username"]])`. Replace every existing `session.` use in the route bodies with `_current_session().`.
  - **`POST /api/login`:**
    - read the JSON body; if `username` or `password` is not a `str`, or `username.strip() == ""`, or `password == ""` → `400 {"error": "Enter both a username and a password"}`;
    - call `authenticate()`; if it returns `None` → `401 {"error": "Username or password is incorrect"}`;
    - else set `login_session["username"] = account.username` and return `200 {"account": {"username", "display_name"}}`;
    - in legacy mode, do not register this route (or return 404).
  - **`GET /api/state`:** in accounts mode, also include `"account": {"username": ..., "display_name": ...}`.

  Update the module docstring to mention spec 015.
- [X] T014 [US1] In `src/web/__main__.py`, depends on T007 and T013; makes T011 pass:
  - add `parser.add_argument("--accounts-file", type=Path, default=Path("accounts.yml"), help=...)`;
  - in `main()`, call `load_accounts(args.accounts_file, args.progress_file)` before `create_app`; on `AccountsFileError`, `print(str(exc), file=sys.stderr)` and `sys.exit(2)`;
  - pass `accounts=accounts` to `create_app`;
  - after the existing "running at" line, print `"Accounts: " + ", ".join(f"{a.username} → {a.progress_file}" for a in accounts)`, which never prints a password.
- [X] T015 [P] [US1] In `src/web/templates/index.html`, per `contracts/login-ui-contract.md`. Makes T012's template assertions pass.
  - **Header:** in `<header class="nav site-header">`, after the brand, add `<span id="account-name" class="account-name text-muted" hidden></span>` and `<button id="logout-button" type="button" class="btn btn-ghost" hidden>Log out</button>`, keeping the existing `#end-session-button`.
  - **Login screen:** as the first section inside `<main id="app">`, after `#warnings`, add `<section id="login-view" class="screen" hidden>` containing a `<form id="login-form" class="login-form">` with:
    - an `<h1>Log in</h1>`;
    - labelled `#login-username` (`type="text" autocomplete="username" autocapitalize="off" spellcheck="false"`) and `#login-password` (`type="password" autocomplete="current-password"`), reusing the existing `.field`/`.input` classes;
    - `<p id="login-error" class="login-error" role="alert" hidden></p>`;
    - `<button type="submit" class="btn btn-primary btn-lg">Log in</button>`.
- [X] T016 [US1] In `src/web/static/app.js`, depends on T013 and T015; makes T012's JS assertions pass.
  - **Views:** register `login: document.getElementById("login-view")` in the `views` map so `showOnly("login")` works.
  - **`showLogin()`:**
    - call `showOnly("login")` and hide `#warnings`, `#step-actions`, `#word-feedback`, `#end-session-button`, `#account-name` and `#logout-button`;
    - call `stopRecording(true)`;
    - focus `#login-username`.
  - **401 handling:** in `fetchState()` and in every other place that `fetch`es or `postJson`s an `/api/` URL (`submitAnswer`, `continueStep`, the select/skip/end/restart/retry/transcribe calls), check `resp.status === 401` and call `showLogin()` before parsing JSON. A small `handleUnauthorized(resp)` helper returning a boolean is fine.
  - **Logged-in header:** in `renderState(state)`, when `state.account` is present, set `#account-name` text to `state.account.display_name || state.account.username` and unhide it and `#logout-button`.
  - **Login form `submit` handler:**
    - call `preventDefault`;
    - if `username.trim()` or `password` is empty, show "Enter both a username and a password" in `#login-error` and do not fetch;
    - else `postJson("/api/login", {username, password})`;
    - on `401`, show "Username or password is incorrect", clear and focus the password field, and keep the username;
    - on `200`, clear both fields, hide the error, and call `fetchState()`.
  - **No storage:** never write credentials to `localStorage` or `sessionStorage`.
- [X] T017 [P] [US1] In `src/web/static/style.css`, using only existing tokens and custom properties (no new colors or fonts, per the Broadsheet handoff in `design_handoff_english_tutor/`):
  - `.login-form`: centered column with `max-width` about 22rem and spacing that matches `.field`;
  - `.login-error`: the existing error/incorrect color token;
  - `.account-name`: `margin-left: auto`, `white-space: nowrap`, `overflow: hidden`, `text-overflow: ellipsis`, `max-width` about 12ch at ≤ 480px;
  - the header must stay on one line at 375px wide with brand, name, "End session" and "Log out", with no horizontal scroll.

**Checkpoint**: US1 works on its own. `pytest` passes, including T009–T012 and every pre-existing test. quickstart.md scenarios 1–4 pass manually.

---

## Phase 4: User Story 2 - Practice at the same time on different devices (Priority: P2)

**Goal**: Two accounts logged in on different devices progress through independent sessions (collection, order, mode, current word, score, sentence review), and one account's slow review doesn't block the other.

**Independent Test**: Two test clients, A as weibo and B as lily, pick different collections and modes and alternate actions. Each client's `/api/state` only changes when that client acts.

### Tests for User Story 2 (write first, confirm they FAIL or would catch a regression)

- [X] T018 [P] [US2] In `tests/integration/test_multi_account_flow.py`, add isolation tests. Use vocab with groups `unit1: receive/收到, give up/放弃` and `unit2: accept/接受`, `offer_choice=True`.
  - **(a) Interleaved sessions:** client A (weibo) `POST /api/select {"collection":"unit1","order":"sequential","mode":"sentence"}` and client B (lily) `POST /api/select {"collection":"unit2","mode":"recall-only"}`. Then alternate A answer `receive`, B answer `accept`, B continue, and assert after each step:
    - A's state keeps `total == 2` and its own `position` and `step`;
    - B's state reaches `complete` with `correct == 1` while A is still at `step == "sentence"`.
  - **(b) Sentence review:** patch `src.web.session_state.request_correction` to return `CorrectionResult(available=True, uses_expression=True, needs_correction=False, corrected=None, explanation="")`. When A submits a sentence, B's state has no `feedback` or `sentence` key, and A's has them.
  - **(c) End session:** B's `POST /api/end` does not change A's `step` or `position`.
  - **(d) Same account, two devices:** two clients both logged in as weibo see the same `step` and `position` after one of them answers (shared session, spec edge case).
- [X] T019 [P] [US2] In `tests/integration/test_web_startup_accounts.py`, add a test that `main()` calls `Flask.run` with `threaded=True` explicitly (recorded kwargs), so one account's long Ollama review can't block the other account (research R3).

### Implementation for User Story 2

- [X] T020 [US2] In `src/web/__main__.py`, change `app.run(host=args.host, port=args.port)` to `app.run(host=args.host, port=args.port, threaded=True)`, making today's implicit Flask default an explicit, tested guarantee. If T018 exposes any shared state between accounts in `src/web/app.py`, for example a leftover use of a single module-level `PracticeSession`, route it through `_current_session()`. `PracticeSession` stays unchanged. Depends on T019 failing, T013, T014.

**Checkpoint**: US1 and US2 both work. quickstart.md scenario 5 passes manually on two devices or browsers.

---

## Phase 5: User Story 3 - Log out and switch accounts on a shared device (Priority: P3)

**Goal**: "Log out" ends the device's login, discards any word in progress without recording it, and returns to the login screen. A login survives browser restarts until logout or a server restart.

**Independent Test**: On one test client: log in as weibo, answer correctly to reach the sentence step, then log out. No attempt is written, `/api/state` returns 401, and logging in as lily gives lily's own `choose` state. The login cookie is persistent (has an expiry).

### Tests for User Story 3 (write first, confirm they FAIL)

- [X] T021 [P] [US3] In `tests/contract/test_web_auth_contract.py`, add logout tests per the contract's `POST /api/logout` section:
  - **Logout responses:** after login, `POST /api/logout` → `200 {"ok": true}`, and a following `GET /api/state` → `401`. `POST /api/logout` without a login → `401` (already covered by T009's parametrized guard; assert again here for clarity).
  - **Cookie persistence:** the `Set-Cookie` header from a successful `POST /api/login` contains `Expires=` (a permanent session, FR-010) and `HttpOnly` and `SameSite=Lax`, and the cookie value does not contain the password.
  - **Re-login without logout:** logging in as lily on a client already logged in as weibo switches the account: `state["account"]["username"] == "lily"`.
- [X] T022 [P] [US3] In `tests/integration/test_multi_account_flow.py`, add logout tests:
  - **(a) Word in progress:** weibo selects everything in sentence mode, answers `receive` correctly (step `sentence`), then logs out. `progress.md` does not exist or has no attempt for `receive`. Logging in as weibo again gives `step == "choose"` (a fresh session, research R7).
  - **(b) Recall-only reveal:** a wrong recall-only answer held in `reveal`, then logout, writes no attempt.
  - **(c) Switching on the same device:** the same client logs out of weibo mid-session and logs in as lily. Lily's state is `choose` with `account.username == "lily"`, and lily's progress file is untouched.
  - **(d) Group-locked start-up:** with `group="unit1", offer_choice=False`, logout followed by re-login gives `step == "recall"` and `position == 1`. `end_session()` would have refused here, which proves `reset()` is used instead.
- [X] T023 [P] [US3] In `tests/unit/test_web_static_assets.py`, add assertions that `app.js` references `/api/logout` and `logout-button`, and that the logout handler calls `showLogin` (string check `"showLogin()"` appears in the file at least twice: once in the 401 handler and once in the logout handler).

### Implementation for User Story 3

- [X] T024 [US3] In `src/web/app.py`, accounts mode only. Depends on T013; makes T021 and T022 pass.
  - In `POST /api/login`, set `login_session.permanent = True` before storing the username, so the 365-day `PERMANENT_SESSION_LIFETIME` from T013 applies (FR-010).
  - Add `POST /api/logout`, which is behind the guard: look up the account, call `app.session_registry.reset(account)` (discards the word in progress unrecorded), call `login_session.clear()`, and return `jsonify({"ok": True})`.
- [X] T025 [US3] In `src/web/static/app.js`, add a click handler on `#logout-button` that calls `postJson("/api/logout")`, whatever the status (`200` or `401`), and then `showLogin()`. Depends on T016 and T024; makes T023 pass.

**Checkpoint**: All three stories work. quickstart.md scenario 6 passes manually, including closing and reopening the browser and restarting the server.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T026 [P] Update `README.md`:
  - **Overview:** the opening paragraph says "single-learner"; reword it to say the web UI supports several learners, each with their own login and history.
  - **New "Accounts (web UI)" subsection** under "Running (web UI)":
    - copy `accounts.example.yml` to `accounts.yml` and edit it;
    - the file format, linking to `specs/015-multi-account-login/contracts/accounts-file-format.md`;
    - the first account owns `progress.md` and others write `progress-<username>.md`;
    - the new `--accounts-file` flag, with a row added to the flags table or a note;
    - logins last until "Log out" or a server restart;
    - plain-text passwords, trusted home network only.
  - **Replace the outdated sentence** "It does not require authentication" in that section.
  - **Caution note:** extend it to say per-account progress files also belong outside `--vocab-dir`.
  - **CLI:** state that the CLI is unchanged and has no login.
- [X] T027 [P] Run `.venv/bin/ruff check .` and fix any issues in new and changed files.
- [X] T028 Run the full suite with `.venv/bin/pytest -q`. Every pre-existing test must pass **unchanged** (`git diff tests/` shows only additions), proving no regression to grading, review, the progress-log format, collection choice, order and mode, recall-only reveal, voice input, or the Broadsheet UI.
- [X] T029 Visual check of the login screen and the logged-in header with the project's `frontend-design` skill workflow: take screenshots at desktop and at 375px mobile width, compare against the Broadsheet style in `design_handoff_english_tutor/`, and fix spacing or overflow in `src/web/static/style.css`. Check there is no horizontal scroll and the header stays on one line at 375px.
- [ ] T030 Run every scenario in `specs/015-multi-account-login/quickstart.md` end-to-end (0–8) against a real `accounts.yml`, including two real devices on the LAN for scenario 5 and the CLI check in scenario 8. A green test suite proves the logic; this pass proves the login and per-account flow actually feel right.
  - *Status (2026-10-02)*: scenarios 0, 2, 3, 4, 6 and 7 were run against a live isolated server through the JSON API (curl), including two concurrent cookie jars standing in for two devices (scenario 5), plus `--help` for scenario 8. Login and header screens were screenshotted at 1280, 390 and 375 px. **Still to do by a person**: clicking through the login form in a real browser (error messages, the Log out button, closing and reopening the browser) and scenario 5 on two physical devices on the LAN.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: none. T001 and T002 are independent.
- **Foundational (Phase 2)**: T005 needs T001, because it loads `accounts.example.yml`. Blocks all user stories.
- **US1 (Phase 3)**: depends on Foundational.
- **US2 (Phase 4)**: depends on US1's T013 and T014, because isolation can only be tested through login. It has no dependency on US3.
- **US3 (Phase 5)**: depends on US1 (T013, T016). It has no dependency on US2.
- **Polish (Phase 6)**: depends on all stories you intend to ship.

### Within Each Phase

- Tests come first and must fail for the right reason before their implementation task:
  - T003 → T006/T007, T004 → T008, T005 → T007;
  - T009/T010 → T013, T011 → T014, T012 → T015/T016;
  - T018/T019 → T020;
  - T021/T022 → T024, T023 → T025.
- T006 comes before T007 and T008, which import `Account`.
- T013 comes before T014 (which passes `accounts=`), T016 (which needs the API), and T024 (same file).
- T015 comes before T016, which needs the DOM ids.

### Parallel Opportunities

- T001 ∥ T002.
- T003 ∥ T004 ∥ T005, then T007 ∥ T008 after T006.
- T009 ∥ T010 ∥ T011 ∥ T012, then T015 ∥ T017 alongside T013.
- After US1: US2 (T018–T020) ∥ US3 (T021–T025). They touch the same test files, so coordinate the edits; their source files differ (`__main__.py` vs `app.py`/`app.js`).
- T026 ∥ T027.

---

## Parallel Example: User Story 1

```bash
# Write all US1 tests together (different files):
Task: "login/guard/state contract tests in tests/contract/test_web_auth_contract.py"
Task: "separate-histories integration tests in tests/integration/test_multi_account_flow.py"
Task: "startup validation + banner tests in tests/integration/test_web_startup_accounts.py"
Task: "login-view + header static assertions in tests/unit/test_web_static_assets.py"

# Then, alongside T013 (app.py):
Task: "login view + header markup in src/web/templates/index.html"
Task: "login form + header styles in src/web/static/style.css"
```

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Phase 1 Setup, then Phase 2 Foundational.
2. Phase 3 US1: login, the 401 guard, and per-account histories.
3. **Stop and validate**: run quickstart scenarios 1–4. Two people on different devices can already practise with separate histories. Concurrent use mostly works through the registry; US2 hardens it and proves it.

### Incremental Delivery

1. Foundation + US1, then validate (MVP).
2. + US2 (explicit threading and isolation tests), then validate scenario 5.
3. + US3 (logout, persistent login), then validate scenario 6.
4. Polish: README, lint, full regression run, visual check, full quickstart.

---

## Notes

- `create_app(accounts=None)` keeps the old no-login behavior **only** so the existing test suite stays unchanged (research R8). The shipped entry point `python -m src.web` always loads accounts, so the real web UI always requires login.
- The Flask cookie session must be imported under a different name (`login_session`) because `app.py` already uses `session` for the `PracticeSession`.
- Never print, log, render, or put a password in an exception message. T003, T009, T011 and T021 each assert this.
- Commit after each task or logical group.
