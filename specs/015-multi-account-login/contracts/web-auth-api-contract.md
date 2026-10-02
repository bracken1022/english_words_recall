# Contract: Web Login API and Per-Account Practice API

Extends `specs/003-web-ui/contracts/web-api-contract.md` (and the later
specs that added `/api/select`, `/api/skip`, `/api/restart`, `/api/end`,
`/api/retry-sentence`, `/api/continue`, `/api/transcribe`). Implemented in
`src/web/app.py`. Covers spec FR-002 – FR-011.

Applies when the app is created with an account list (always, via
`python -m src.web`). When `create_app(accounts=None)` — only in the
pre-existing test suite — none of this applies and the API behaves exactly
as before (research R8).

## Login cookie

A Flask signed session cookie holding only a random login id, which the
server maps to a username in memory. `HttpOnly`, `SameSite=Lax`, permanent
with a 365-day lifetime; invalidated by logout (the id is deleted, so a
saved copy of the cookie stops working) and by server restart.

## `POST /api/login`

Always reachable (no login needed).

Request:

```json
{ "username": "Weibo ", "password": "change-me" }
```

| Case | Status | Body | Cookie |
|---|---|---|---|
| Username (trimmed, case-insensitive) and password (exact) match an account | `200` | `{"account": {"username": "weibo", "display_name": "Weibo"}}` | set to a new login id for `weibo` (replacing any previous login) |
| No match — unknown username **or** wrong password | `401` | `{"error": "Username or password is incorrect"}` (identical for both causes) | unchanged |
| Missing/non-string field, or either field empty after trimming the username | `400` | `{"error": "Enter both a username and a password"}` | unchanged |

`display_name` is `null` when not configured. The response never contains
the password.

## `POST /api/logout`

Requires login (else `401` as below).

- Forgets the login id server-side and clears the cookie.
- Replaces the account's practice session with a fresh one; any word in
  progress is discarded and **not** written to the progress history.
- Response: `200` `{"ok": true}`.

## Guard on every other `/api/*` endpoint

`GET /api/state`, `POST /api/answer`, `/api/sentence`, `/api/select`,
`/api/skip`, `/api/restart`, `/api/end`, `/api/retry-sentence`,
`/api/continue`, `/api/transcribe`, `/api/logout`, and any future `/api/*`
route:

- No login cookie, or its login id is unknown (forged, logged out, or from
  before a restart) →
  `401` `{"error": "login required"}`; nothing is read from or written to
  any practice session or progress history.
- Otherwise → the request acts on **that account's** practice session only;
  request/response shapes are unchanged from the earlier contracts.

`GET /` and `/static/*` are always served (the page itself renders the
login screen).

## `GET /api/state` — added field

When logged in, the existing response gains:

```json
{
  "step": "choose",
  "account": { "username": "lily", "display_name": "Lily" },
  "...": "existing fields unchanged"
}
```

## Isolation guarantees

- Account A's requests never change account B's `step`, collection, order,
  mode, `position`, score, pending attempt, or sentence feedback.
- Attempts made while logged in as A are appended only to A's progress
  file.
- Two browsers logged in to the **same** account share one practice session
  (same as one learner with two tabs today).
