"""One PracticeSession per logged-in account (spec 015, data-model.md
"SessionRegistry"). PracticeSession itself is unchanged; each account's
instance just writes to that account's own progress file."""

import threading
from pathlib import Path

from src.models.account import Account
from src.web.session_state import PracticeSession


class SessionRegistry:
    def __init__(
        self,
        vocab_dir: Path,
        group: str | None,
        offer_choice: bool,
        order: str,
        mode: str,
    ):
        self._vocab_dir = vocab_dir
        self._group = group
        self._offer_choice = offer_choice
        self._order = order
        self._mode = mode
        self._sessions: dict[str, PracticeSession] = {}
        self._lock = threading.Lock()

    def _new_session(self, account: Account) -> PracticeSession:
        return PracticeSession(
            vocab_dir=self._vocab_dir,
            progress_file=account.progress_file,
            group=self._group,
            offer_choice=self._offer_choice,
            order=self._order,
            mode=self._mode,
        )

    def get(self, account: Account) -> PracticeSession:
        with self._lock:
            session = self._sessions.get(account.username)
            if session is None:
                session = self._new_session(account)
                self._sessions[account.username] = session
            return session

    def reset(self, account: Account) -> None:
        """Start the account over (logout, research.md R7): the word in
        progress is discarded without being recorded."""
        with self._lock:
            self._sessions[account.username] = self._new_session(account)
