"""One PracticeSession per logged-in account (spec 015, data-model.md
"SessionRegistry"). PracticeSession itself is unchanged; each account's
instance just writes to that account's own progress file."""

import threading
from pathlib import Path

from src.models.account import Account
from src.services.word_lists import WordListStore
from src.web.session_state import PracticeSession


class SessionRegistry:
    def __init__(
        self,
        vocab_dir: Path,
        group: str | None,
        offer_choice: bool,
        order: str,
        mode: str,
        word_lists: WordListStore | None = None,
    ):
        self._vocab_dir = vocab_dir
        self._group = group
        self._offer_choice = offer_choice
        self._order = order
        self._mode = mode
        self._word_lists = word_lists
        self._sessions: dict[str, PracticeSession] = {}
        self._lock = threading.Lock()

    def _vocab_dir_for(self, account: Account) -> Path:
        """The account's own lists once it has any, else the shared folder
        (spec 016, research.md R2)."""
        if self._word_lists is None:
            return self._vocab_dir
        return self._word_lists.effective_dir(account, self._vocab_dir)

    def _new_session(self, account: Account) -> PracticeSession:
        return PracticeSession(
            vocab_dir=self._vocab_dir_for(account),
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

    def refresh_vocab(self, account: Account) -> None:
        """Re-point the account's live session after its lists changed."""
        with self._lock:
            session = self._sessions.get(account.username)
            if session is not None:
                session.set_vocab_dir(self._vocab_dir_for(account))
