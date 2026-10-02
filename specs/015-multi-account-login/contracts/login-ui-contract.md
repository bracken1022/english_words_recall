# Contract: Login Screen and Account Header (web UI)

Implemented in `src/web/templates/index.html`, `src/web/static/app.js`,
`src/web/static/style.css`. Follows the existing Broadsheet style (spec 014
handoff); reuse existing `.screen`, `.field`, `.btn`, `.btn-primary`,
`.btn-ghost` classes — no new visual language. Covers spec FR-002, FR-004,
FR-005, FR-009.

## When the login screen shows

- On page load, the front end calls `GET /api/state`. A `401` response
  shows `#login-view` and hides every other `.screen`, the step actions, and
  the header's account controls.
- Any later API call that returns `401` (e.g. after a server restart)
  does the same — no practice screen remains visible.

## `#login-view`

- Heading: "Log in".
- Fields: `#login-username` (text, `autocomplete="username"`,
  `autocapitalize="off"`, `spellcheck="false"`) and `#login-password`
  (`type="password"`, `autocomplete="current-password"`), each with a
  visible label.
- Primary button "Log in" (`type="submit"`); Enter in either field submits.
- If either field is empty, don't send the request; show
  "Enter both a username and a password" in `#login-error`.
- On `401`: show "Username or password is incorrect" in `#login-error`
  (`role="alert"`), clear the password field, keep the username, focus the
  password field.
- On `200`: clear both fields and the error, then render the normal state
  (`GET /api/state`), focusing the screen's primary input as today.
- The password is never echoed or stored by the page (no `localStorage`).

## Header account controls (`.site-header`)

- While logged in: show `#account-name` with the display label
  (`display_name` or `username`) and a `#logout-button` ("Log out",
  `.btn-ghost`). Both are visible on every practice screen, beside the
  existing "End session" button.
- "Log out" calls `POST /api/logout`, then shows `#login-view`.
- At phone width (≤ 480 px) the header still fits on one line with no
  horizontal scroll; the account name may truncate with an ellipsis.

## Accessibility

- Login form fields have `<label for>`; the error region is announced.
- Focus moves to `#login-username` when the login screen appears.
