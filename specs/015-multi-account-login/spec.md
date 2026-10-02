# Feature Specification: Multiple Learner Accounts with Simple Login

**Feature Branch**: `015-multi-account-login`

**Created**: 2026-10-02

**Status**: Draft

**Input**: User description: "I want to support multi accounts, such as I can login with my account. My wife can login by her. Now no need to implement the account verification. We can give the hardcoded account credentials"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Log in as yourself and practice with your own history (Priority: P1)

Two people in the same household share one running English Tutor. Today
the web UI has no notion of who is practicing: everyone's attempts land
in the same progress history, so one person's mistakes and successes are
mixed up with the other's. Each person wants to open the web UI, log in
with their own account (a username and password the household's operator
has set up in advance), and practice knowing that everything they do is
recorded under their own name only.

**Why this priority**: This is the whole ask — without separating who is
practicing, nothing else in the feature has value.

**Independent Test**: Can be fully tested with two pre-configured
accounts: log in as account A, practice a few words, log out; log in as
account B, practice a few words; then confirm A's history contains only
A's attempts and B's history contains only B's attempts.

**Acceptance Scenarios**:

1. **Given** the operator has configured accounts for two learners,
   **When** a learner opens the web UI without being logged in, **Then**
   they see a login screen instead of the practice screens.
2. **Given** the login screen, **When** a learner enters a configured
   username and its matching password, **Then** they are taken to the
   word-set choice screen (or straight into practice, if the tutor was
   started locked to one group) and the screen shows which account is
   logged in.
3. **Given** a learner is logged in as account A, **When** they complete
   practice attempts, **Then** those attempts are recorded only in
   account A's progress history.
4. **Given** account A has existing practice history, **When** a learner
   logs in as account B, **Then** nothing from A's history appears in or
   affects B's session.

---

### User Story 2 - Practice at the same time on different devices (Priority: P2)

Both learners want to practice simultaneously — one on a phone, one on a
laptop — against the same running tutor, without either one's session
interfering with the other's (current word, score, chosen collection,
order, and mode).

**Why this priority**: Separate histories (P1) are the core need, but
today the tutor keeps a single shared practice session, so two people
practicing at once would trample each other's progress through a word
set. Independent sessions make multi-account usable in practice.

**Independent Test**: Can be fully tested by logging in as A on one
device and B on another, starting different collections with different
settings, and alternating answers between the two devices; each device
continues exactly where its own learner left off.

**Acceptance Scenarios**:

1. **Given** A and B are both logged in on different devices, **When** A
   picks collection X in random order and B picks collection Y in
   sequential order, **Then** each sees only their own collection, order,
   current word, and score.
2. **Given** A is mid-session, **When** B answers a word, ends their
   session, or returns to the word sets, **Then** A's current word and
   score are unchanged.
3. **Given** A is waiting on a sentence review, **When** B submits a
   sentence for review, **Then** each receives only the feedback for their
   own sentence.

---

### User Story 3 - Log out and switch accounts on a shared device (Priority: P3)

The household may share a single tablet. A learner who has finished wants
to log out so the next person can log in as themselves, and nobody
accidentally practices under someone else's name.

**Why this priority**: Useful for shared devices, but each person using
their own device already works with P1 and P2 alone.

**Independent Test**: Can be fully tested on one browser: log in as A,
log out, confirm the login screen returns and practice screens are
unreachable, then log in as B and confirm the session is B's.

**Acceptance Scenarios**:

1. **Given** a learner is logged in, **When** they choose "Log out",
   **Then** they return to the login screen and can no longer reach any
   practice screen or action until someone logs in again.
2. **Given** A logged out mid-session, **When** B logs in on the same
   device, **Then** B starts from the word-set choice screen with B's own
   state, not A's half-finished session.
3. **Given** a learner logged in earlier on a device and did not log out,
   **When** they reopen the web UI on that device later (while the tutor
   is still running), **Then** they are still logged in as themselves.

---

### Edge Cases

- Wrong password or unknown username: login is refused with a single
  generic message ("Username or password is incorrect") that does not
  reveal which part was wrong; the learner stays on the login screen.
- Empty username or password: the login is not attempted and the learner
  is asked to fill in both fields.
- Username matching ignores letter case and surrounding spaces
  ("Alice", " alice " both match "alice"); passwords are matched exactly.
- A learner who is not logged in tries to perform any practice action
  directly (answer, review a sentence, choose a collection, etc.): the
  action is refused with no change to anyone's state, and the web UI
  returns to the login screen.
- The same account logs in on two devices at once: both devices are
  allowed and share that account's single practice session (the same as
  the tutor behaves today for one person on two tabs).
- A logged-out learner's half-finished session: the word in progress is
  not logged, matching today's "End session" behavior.
- The tutor is restarted: in-progress practice sessions are lost (as
  today), and learners may need to log in again; all recorded history is
  kept.
- No accounts are configured: the tutor refuses to start the web UI and
  tells the operator why, rather than running with nobody able to log in.
- Two configured accounts share the same username (ignoring case): the
  tutor refuses to start and names the duplicate.
- The existing, pre-feature progress history: it remains readable and
  becomes the history of the first configured account, so the original
  user's past practice is not lost or orphaned.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST support a fixed set of learner accounts,
  each with a unique username, a password, and an optional display name,
  defined in advance by the operator. There is no in-app sign-up,
  account editing, password reset, or email/identity verification.
- **FR-002**: The web UI MUST require a learner to log in before showing
  any practice screen or accepting any practice action.
- **FR-003**: Login MUST succeed only when the entered username matches a
  configured account (case-insensitive, surrounding whitespace ignored)
  and the entered password exactly matches that account's password.
- **FR-004**: A failed login MUST show one generic error message that does
  not reveal whether the username or the password was wrong.
- **FR-005**: Once logged in, the web UI MUST display which account is
  active (display name if set, otherwise username) on every practice
  screen.
- **FR-006**: Each account MUST have its own separate practice history;
  every recorded attempt MUST go only to the history of the account that
  made it.
- **FR-007**: Each account MUST have its own independent practice session
  state (chosen collection, order, mode, current word, score, pending
  sentence review), so that one account's actions never change another
  account's session.
- **FR-008**: All accounts MUST practice from the same shared vocabulary
  content; adding or editing vocabulary benefits every account.
- **FR-009**: Learners MUST be able to log out from any practice screen;
  logging out MUST end that device's access until a login occurs again,
  and MUST discard (not log) any word in progress.
- **FR-010**: A login on a device MUST persist across page reloads and
  browser restarts on that device for as long as the tutor keeps running,
  until the learner logs out.
- **FR-011**: Any practice action requested without a valid login MUST be
  refused without changing any account's state or history.
- **FR-012**: The pre-existing practice history MUST be preserved and
  treated as the history of the first configured account.
- **FR-013**: The tutor MUST refuse to start the web UI, with a clear
  message to the operator, if no accounts are configured or if two
  accounts share a username.
- **FR-014**: The command-line tutor MUST keep working as it does today
  (single learner, no login).
- **FR-015**: Passwords MUST never be shown in the web UI, written to any
  practice history, or printed in startup output or error messages.

### Key Entities

- **Learner Account**: A person who can log in. Attributes: username
  (unique, case-insensitive), password, optional display name. Defined by
  the operator; fixed while the tutor runs.
- **Login (device session)**: The link between one browser/device and one
  learner account, created at login and ended at logout. Determines whose
  practice session and history a request acts on.
- **Practice Session**: The existing in-progress practice state, now owned
  by exactly one learner account instead of shared by everyone.
- **Practice History**: The existing human-readable log of attempts, now
  one per learner account.

### Data Handling (Constitution Principle III)

- **Collected**: for each account, the username, password, and optional
  display name supplied by the operator; per-account practice history
  (the same attempt data recorded today, now separated by account).
- **Why**: to tell learners apart so each sees and builds only their own
  practice history.
- **Access**: a learner can only act on and add to their own account's
  history through the web UI. Histories remain plain files on the
  operator's own machine; nothing is sent anywhere new.
- **Not done**: no account data or history is used for any other purpose
  or shared with any third party.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A learner can go from opening the web UI to practicing their
  first word, including logging in, in under 30 seconds.
- **SC-002**: After two learners each complete a practice session, 100% of
  each learner's attempts appear in their own history and 0% appear in
  the other's.
- **SC-003**: Two learners practicing at the same time on separate devices
  for 20 alternating answers see zero changes to their own current word,
  score, or settings caused by the other learner.
- **SC-004**: 100% of practice actions attempted without a valid login are
  refused, with no change to any history.
- **SC-005**: The original user's practice history from before this
  feature is fully present under their account after upgrading (no
  attempts lost).
- **SC-006**: After logging out, 0 practice screens or actions are
  reachable on that device until a new login.

## Assumptions

- This is a trusted household setup on the local network, as today:
  the login exists to separate learners, not to defend against attackers.
  Passwords are a simple shared-secret check with no lockout, rate limiting,
  expiry, or strength rules, and traffic stays on the local network
  unencrypted, as it does today.
- "Hardcoded account credentials" means the operator defines the accounts
  (initially two: the original user and their spouse) in a fixed list
  that is read when the tutor starts; changing accounts means editing that
  list and restarting the tutor.
- Vocabulary content is shared by all accounts; only history and session
  state are per-account.
- Login is only for the web UI; the command-line tutor remains a
  single-learner tool and keeps using the existing history.
- The order in which accounts are listed is meaningful only for FR-012
  (the first account inherits the existing history).
- Logins do not need to survive a tutor restart; asking learners to log in
  again after a restart is acceptable.
- The existing start-up options that lock the tutor to one group, order,
  or mode apply to every account's session the same way they apply to the
  single session today.
