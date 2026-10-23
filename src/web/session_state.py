"""The shared, in-memory practice-session state machine (spec 003,
data-model.md). A thin orchestration layer over vocabulary_loader,
matcher and progress_log.

Spec 021 replaced sentence writing and review with example sentences:
in the "example" modes every answer goes to "reveal", which carries the
word's example (made in the background by an ExampleService as soon as
the word comes up), and the attempt is recorded once the learner moves on.
"""

import random
from datetime import UTC, datetime
from pathlib import Path

from src.lib.word_diff import AttemptComparison, compare
from src.models.practice_attempt import PracticeAttempt
from src.services.matcher import grade_answer
from src.services.progress_log import append_attempt
from src.services.vocabulary_loader import load_vocabulary

Step = str  # "empty" | "choose" | "recall" | "reveal" | "sentence-recall" | "complete"

UNGROUPED_KEY = "__ungrouped__"
MODES = ("recall-only", "example", "example-recall")
DEFAULT_MODE = "example"
SENTENCE_RECALL_MARKS = ("reveal", "got", "not_yet", "skip")


class WrongStepError(Exception):
    """Raised when an action is requested for the wrong step (no state change)."""


def normalize_mode(mode: str | None) -> str:
    """The practice mode to use: "sentence" (spec 012's old default) and
    anything unknown mean the default "example" mode (spec 021)."""
    return mode if mode in MODES else DEFAULT_MODE


class PracticeSession:
    def __init__(
        self,
        vocab_dir: Path,
        progress_file: Path,
        group: str | None = None,
        offer_choice: bool = False,
        order: str = "sequential",
        mode: str = DEFAULT_MODE,
        item_filter=None,
        example_service=None,
        voice_available: bool = False,
        correction_service=None,
    ):
        """*offer_choice* opts into the interactive collection-choice step
        (spec 007); without it the session starts straight away on every
        word (or only *group*'s), in *order* ("sequential" or "random",
        spec 011) and *mode* (spec 021: "recall-only", "example" [default]
        or "example-recall"). In the interactive branch select_collection()
        decides order and mode instead.

        *item_filter* (spec 020) drops words this learner removed from the
        shared sets; *example_service* (spec 021) makes and keeps example
        sentences — None means no examples are offered. *voice_available*
        (spec 022) says whether speech-to-text is installed, for the
        sentence-recall Speak button. *correction_service* (spec 023) checks
        each word with Qwen in the background the first time it comes up.
        """
        self.progress_file = progress_file
        self.vocab_dir = vocab_dir
        self.warnings: list[str] = []
        self.current_index = 0
        self.pending_attempt: dict | None = None
        self.correct_count = 0
        self.item_filter = item_filter
        self.example_service = example_service
        self.correction_service = correction_service
        self.pending_undo: dict | None = None
        self.sentence_revealed = False
        self.voice_available = voice_available

        items, warnings = self._load(vocab_dir)
        self.warnings = warnings
        self.all_items = items

        interactive = offer_choice and group is None
        self.group_locked = not interactive

        if interactive:
            self.items = []
            self.mode = DEFAULT_MODE
            self.step: Step = "choose" if self.all_items else "empty"
        else:
            if group is not None:
                items = [item for item in items if item.group == group]
            if order == "random":
                random.shuffle(items)
            self.items = items
            self.mode = normalize_mode(mode)
            self.step = "recall" if self.items else "empty"
            self._word_started()

    @property
    def recall_only(self) -> bool:
        return self.mode == "recall-only"

    def _load(self, vocab_dir: Path) -> tuple[list, list[str]]:
        items, warnings = load_vocabulary(vocab_dir)
        if self.item_filter is not None:
            items = self.item_filter(items)
        return items, warnings

    def _word_started(self) -> None:
        """A new word is up: start making its example and, in every mode,
        checking its values (spec 023) in the background."""
        if self.step != "recall":
            return
        if not self.recall_only and self.example_service is not None:
            self.example_service.prepare(self.current_item)
        if self.correction_service is not None:
            self.correction_service.prepare(self.current_item)

    @property
    def current_item(self):
        return self.items[self.current_index]

    def _available_collections(self) -> list[dict]:
        """List of {"key", "label", "count"} choices derived from
        self.all_items, per data-model.md: "practice everything" (key
        None) always first, then real group values alphabetically, then
        an "ungrouped" bucket (key UNGROUPED_KEY) last, only if any item
        has group is None."""
        named: dict[str, int] = {}
        ungrouped_count = 0
        for item in self.all_items:
            if item.group is None:
                ungrouped_count += 1
            else:
                named[item.group] = named.get(item.group, 0) + 1

        collections = [
            {"key": None, "label": "Practice everything", "count": len(self.all_items)}
        ]
        for key in sorted(named):
            collections.append({"key": key, "label": key, "count": named[key]})
        if ungrouped_count:
            collections.append(
                {"key": UNGROUPED_KEY, "label": "Ungrouped words", "count": ungrouped_count}
            )
        return collections

    def submit_answer(self, answer: str) -> dict:
        self.pending_undo = None
        if self.step != "recall":
            raise WrongStepError("not awaiting an answer")

        item = self.current_item
        correct = grade_answer(item, answer)
        # Every answer is shown on "reveal" (with the example, in the
        # example modes) and recorded when the learner moves on.
        self.pending_attempt = {
            "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
            "item": item.english,
            "answer": answer,
            "correct": correct,
        }
        self.step = "reveal"
        return {"correct": correct, "accepted_expressions": item.accepted_expressions()}

    def select_collection(
        self, key: str | None, order: str = "sequential", mode: str = DEFAULT_MODE
    ) -> None:
        """Scope the session to one collection (spec 007): key is None for
        "practice everything", UNGROUPED_KEY for untagged items, or a real
        group value. Valid only from "choose"; resets progress counters
        for the new pass, preserving self.all_items's order unless *order*
        is "random" (spec 011). *mode* is normalised by normalize_mode()."""
        self.pending_undo = None
        if self.step != "choose":
            raise WrongStepError("not choosing a collection")

        if key is None:
            self.items = list(self.all_items)
        elif key == UNGROUPED_KEY:
            self.items = [item for item in self.all_items if item.group is None]
        else:
            self.items = [item for item in self.all_items if item.group == key]

        if order == "random":
            random.shuffle(self.items)

        self.mode = normalize_mode(mode)
        self.current_index = 0
        self.pending_attempt = None
        self.correct_count = 0
        self.step = "recall" if self.items else "empty"
        self._word_started()

    def _record_and_advance(self) -> None:
        """Record the word's held attempt, tally it, and go on to the next
        word or "complete"."""
        append_attempt(self.progress_file, PracticeAttempt(**self.pending_attempt))
        if self.pending_attempt["correct"]:
            self.correct_count += 1
        self.pending_attempt = None
        self.sentence_revealed = False
        self.current_index += 1
        self.step = "complete" if self.current_index >= len(self.items) else "recall"
        self._word_started()

    def continue_to_next(self) -> None:
        """Move on from "reveal". In the example-recall mode, a word with
        a ready example goes to "sentence-recall" first (spec 021 US2)."""
        self.pending_undo = None
        if self.step == "complete":
            return
        if self.step != "reveal":
            raise WrongStepError("not ready to continue")
        if (
            self.mode == "example-recall"
            and self.example_service is not None
            and self.example_service.get(self.current_item)
        ):
            self.step = "sentence-recall"
            self.sentence_revealed = False
            return
        self._record_and_advance()

    def can_transcribe(self) -> bool:
        """Voice is only for recalling a sentence, before it is shown
        (spec 022, FR-001)."""
        return self.step == "sentence-recall" and not self.sentence_revealed

    def sentence_recall_action(
        self, mark: str, attempt: str | None = None
    ) -> AttemptComparison | None:
        """The learner's self-check of the example sentence (spec 021 US2):
        "reveal" shows the sentence; "got" / "not_yet" record the attempt
        with that mark and move on; "skip" records it without a mark.

        On "reveal", the learner's *attempt* (typed or spoken) is compared
        with the sentence and the comparison returned (spec 022, FR-012).
        The attempt itself is never kept, and other marks ignore it."""
        if mark not in SENTENCE_RECALL_MARKS:
            raise ValueError(f"unknown mark {mark!r}")
        self.pending_undo = None
        if self.step != "sentence-recall":
            raise WrongStepError("not recalling a sentence")
        if mark == "reveal":
            self.sentence_revealed = True
            example = self.example_service.get(self.current_item) if self.example_service else None
            if not attempt or not example:
                return None
            return compare(attempt, example["sentence"])
        if mark != "skip":
            self.pending_attempt["sentence_recall"] = mark
        self._record_and_advance()
        return None

    def renew_example(self) -> dict:
        """Replace the current word's example with a new one (spec 021).
        Raises ExampleUnavailable when none can be made right now."""
        if self.step not in ("reveal", "sentence-recall") or self.example_service is None:
            raise WrongStepError("no example to renew")
        return self.example_service.renew(self.current_item)

    def restart(self) -> None:
        """Return to the collection-choice screen (spec 007), reloading
        vocabulary from disk so files added/removed/edited since this
        session started are picked up. Valid only from "complete", and
        only when a collection wasn't locked in at startup."""
        self.pending_undo = None
        if self.step != "complete" or self.group_locked:
            raise WrongStepError("not ready to restart")

        items, warnings = self._load(self.vocab_dir)
        self.warnings = warnings
        self.all_items = items
        self.step = "choose" if self.all_items else "empty"

    def set_vocab_dir(self, vocab_dir: Path) -> None:
        """Point the session at a different vocabulary folder (spec 016:
        an account switches between the shared folder and its own uploaded
        lists). The word-set screen picks it up right away; a session in
        progress, or one locked to a group at startup, keeps its words and
        only uses the new folder at its next reload (research.md R3)."""
        self.vocab_dir = vocab_dir
        if self.group_locked or self.step not in ("choose", "empty"):
            return
        items, warnings = self._load(vocab_dir)
        self.warnings = warnings
        self.all_items = items
        self.step = "choose" if self.all_items else "empty"

    def end_session(self) -> None:
        """Abandon the session mid-word and return to the collection-choice
        screen (Broadsheet redesign's "End session"). The word in progress
        is discarded unrecorded; words already finished stay recorded.
        Only offered when a collection wasn't locked in at startup."""
        self.pending_undo = None
        if self.group_locked or self.step not in ("recall", "reveal", "sentence-recall"):
            raise WrongStepError("no session to end")

        self.pending_attempt = None
        self.sentence_revealed = False
        items, warnings = self._load(self.vocab_dir)
        self.warnings = warnings
        self.all_items = items
        self.step = "choose" if self.all_items else "empty"

    def remove_current(self, remove_fn) -> dict:
        """Take the current word out of practice for good (spec 020).
        *remove_fn(item)* deletes it from its file (or hides it) and
        returns what undo needs; it runs first, so a failure leaves the
        session as it was. An attempt already made is logged as on
        continue; at recall nothing was answered, so nothing is."""
        if self.step not in ("recall", "reveal", "sentence-recall"):
            raise WrongStepError("no word to remove")
        item = self.current_item
        token = remove_fn(item)

        if self.step != "recall":
            append_attempt(self.progress_file, PracticeAttempt(**self.pending_attempt))
            if self.pending_attempt["correct"]:
                self.correct_count += 1
        self.pending_attempt = None
        self.sentence_revealed = False

        index = self.current_index
        del self.items[index]
        all_index = None
        if self.all_items is not self.items:  # a locked session shares one list
            all_index = next(i for i, other in enumerate(self.all_items) if other is item)
            del self.all_items[all_index]
        self.step = "complete" if self.current_index >= len(self.items) else "recall"
        self.pending_undo = {"item": item, "index": index, "all_index": all_index, "token": token}
        self._word_started()
        return {"english": item.english, "chinese": item.chinese}

    def undo_remove(self, restore_fn) -> None:
        """Bring back the word removed last, as the current word, if the
        learner hasn't done anything since. *restore_fn(token)* puts it
        back in its file first, so a failure changes nothing here."""
        if self.pending_undo is None:
            raise WrongStepError("nothing to undo")
        undo = self.pending_undo
        if undo["token"] is not None:
            restore_fn(undo["token"])
        self.items.insert(undo["index"], undo["item"])
        if undo["all_index"] is not None:
            self.all_items.insert(undo["all_index"], undo["item"])
        self.current_index = undo["index"]
        self.step = "recall"
        self.pending_undo = None

    def _example_fields(self, item) -> dict:
        if self.recall_only:
            return {"example": None, "example_status": "off"}
        if self.example_service is None:
            return {"example": None, "example_status": "unavailable"}
        example = self.example_service.get(item)
        status = "ready" if example else self.example_service.status(item)
        if self.step == "sentence-recall" and example and not self.sentence_revealed:
            # The sentence is what's being recalled: withheld until revealed.
            example = {"sentence": None, "translation": example["translation"]}
        return {"example": example, "example_status": status}

    def state(self) -> dict:
        base = {"step": self.step, "warnings": self.warnings}
        if self.step == "choose":
            base["collections"] = self._available_collections()
            return base
        if self.step == "complete":
            base["total"] = len(self.items)
            base["correct"] = self.correct_count
            base["can_restart"] = not self.group_locked
            return base
        if self.step == "empty":
            return base

        item = self.current_item
        base["chinese"] = item.chinese
        # A hint shown with the meaning, never the answer (spec 019).
        base["pos"] = list(item.pos)
        base["position"] = self.current_index + 1
        base["total"] = len(self.items)
        base["can_end_session"] = not self.group_locked
        base["mode"] = self.mode

        if self.step in ("reveal", "sentence-recall"):
            base["accepted_expressions"] = item.accepted_expressions()
            # Revealed with the answer, never during recall (spec 017).
            base["ipa"] = item.ipa
            base["answer"] = self.pending_attempt["answer"]
            base["correct"] = self.pending_attempt["correct"]
            base.update(self._example_fields(item))
            # Fields a check corrected while the learner answered (spec 023).
            base["corrected"] = (
                self.correction_service.corrected_fields(item) if self.correction_service else []
            )
        if self.step == "sentence-recall":
            base["sentence_revealed"] = self.sentence_revealed
            base["voice_available"] = self.voice_available

        return base
