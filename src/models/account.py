"""Account: an operator-defined learner who can log in to the web UI
(spec 015, data-model.md). The password is excluded from repr so it can't
leak into logs or tracebacks (FR-015)."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Account:
    username: str
    password: str = field(repr=False)
    display_name: str | None = None
    progress_file: Path = Path("progress.md")

    @property
    def label(self) -> str:
        return self.display_name or self.username
