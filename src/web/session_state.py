"""The shared, in-memory practice-session state machine (spec 003,
data-model.md). A thin orchestration layer over the existing, unchanged
services — vocabulary_loader, matcher, llm_client.request_correction,
progress_log — introducing no new grading/review/persistence logic."""

import random
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from src.models.practice_attempt import PracticeAttempt
from src.services.llm_client import CorrectionResult, request_correction
from src.services.matcher import grade_answer
from src.services.progress_log import append_attempt
from src.services.vocabulary_loader import load_vocabulary

Step = str  # "empty" | "choose" | "recall" | "sentence" | "feedback" | "reveal" | "complete"

UNGROUPED_KEY = "__ungrouped__"


class WrongStepError(Exception):
    """Raised when an action is requested for the wrong step (no state change)."""


class PracticeSession:
    def __init__(
        self,
        vocab_dir: Path,
        progress_file: Path,
        group: str | None = None,
        offer_choice: bool = False,
        order: str = "sequential",
        mode: str = "sentence",
        item_filter=None,
    ):
        """*offer_choice* opts into the interactive collection-choice step
        (spec 007); it defaults to False so every existing caller that
        doesn't know about this feature keeps today's exact behavior
        (group=None -> immediate, unfiltered "recall"). Only
        src/web/__main__.py sets it, and only when no --group was given —
        an explicit *group* always wins over *offer_choice* (data-model.md).

        *order* ("sequential" [default] or "random", spec 011) is only
        consumed here in the locked branch below — when *offer_choice* wins
        instead, select_collection()'s own *order* argument governs it.

        *mode* ("sentence" [default] or "recall-only", spec 012) resolves
        into self.recall_only, which (unlike order) is stored and consulted
        again on every submit_answer() call for the rest of the session. In
        the interactive branch it's just a placeholder (False) — governed
        instead by select_collection()'s own *mode* argument.
        """
        self.progress_file = progress_file
        self.vocab_dir = vocab_dir
        self.warnings: list[str] = []
        self.current_index = 0
        self.pending_attempt: dict | None = None
        self.last_correction: CorrectionResult | None = None
        self._review_in_progress = False
        self.correct_count = 0
        # Spec 020: drops words this learner removed from the shared sets.
        self.item_filter = item_filter
        self.pending_undo: dict | None = None

        items, warnings = self._load(vocab_dir)
        self.warnings = warnings
        self.all_items = items

        interactive = offer_choice and group is None
        self.group_locked = not interactive

        if interactive:
            self.items = []
            self.recall_only = False
            self.step: Step = "choose" if self.all_items else "empty"
        else:
            if group is not None:
                items = [item for item in items if item.group == group]
            if order == "random":
                random.shuffle(items)
            self.items = items
            self.recall_only = mode == "recall-only"
            self.step = "recall" if self.items else "empty"

    def _load(self, vocab_dir: Path) -> tuple[list, list[str]]:
        items, warnings = load_vocabulary(vocab_dir)
        if self.item_filter is not None:
            items = self.item_filter(items)
        return items, warnings

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
        attempt = {
            "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
            "item": item.english,
            "answer": answer,
            "correct": correct,
        }

        self.pending_attempt = attempt
        if correct and not self.recall_only:
            self.step = "sentence"
        else:
            # Broadsheet redesign: only a correct recall in sentence mode
            # earns the sentence step. Every other outcome (any recall-only
            # answer, or a wrong answer in sentence mode) holds in "reveal"
            # until an explicit continue, which records the attempt (spec
            # 013's hold, now used for every result the learner must see).
            self.step = "reveal"

        return {"correct": correct, "accepted_expressions": item.accepted_expressions()}

    def submit_sentence(
        self,
        sentence: str,
        base_url: str,
        model: str,
        correction_fn: Callable[..., CorrectionResult] | None = None,
    ) -> dict:
        self.pending_undo = None
        if self.step != "sentence":
            raise WrongStepError("not awaiting a sentence")
        if self._review_in_progress:
            raise WrongStepError("a sentence review is already in progress")

        # Resolved from the module global at call time (not bound as a
        # default argument) so tests can patch `request_correction` here.
        if correction_fn is None:
            correction_fn = request_correction

        self._review_in_progress = True
        try:
            item = self.current_item
            result = correction_fn(item.english, sentence, base_url=base_url, model=model)
        finally:
            self._review_in_progress = False

        self.last_correction = result

        if not result.available:
            feedback = "correction unavailable"
        elif result.uses_expression is False:
            feedback = "missing target expression"
        elif result.needs_correction:
            feedback = f"corrected: {result.corrected}"
        else:
            feedback = "already correct"

        self.pending_attempt["sentence"] = sentence
        self.pending_attempt["feedback"] = feedback

        attempt = PracticeAttempt(**self.pending_attempt)
        append_attempt(self.progress_file, attempt)

        self.step = "feedback"
        return {
            "available": result.available,
            "uses_expression": result.uses_expression,
            "needs_correction": result.needs_correction,
            "corrected": result.corrected,
            "explanation": result.explanation,
        }

    def select_collection(
        self, key: str | None, order: str = "sequential", mode: str = "sentence"
    ) -> None:
        """Scope the session to one collection (spec 007): key is None for
        "practice everything", UNGROUPED_KEY for untagged items, or a real
        group value. Valid only from "choose"; resets progress counters
        for the new pass, preserving self.all_items's order unless *order*
        is "random" (spec 011), in which case it's shuffled once here.
        *mode* ("sentence" [default] or "recall-only", spec 012) resolves
        self.recall_only for the whole session that follows."""
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

        self.recall_only = mode == "recall-only"
        self.current_index = 0
        self.pending_attempt = None
        self.last_correction = None
        self.correct_count = 0
        self.step = "recall" if self.items else "empty"

    def skip_sentence(self) -> None:
        """Skip the sentence-writing step for the current item without a
        correction request, recording the recall outcome as-is (spec 006).
        Goes straight from "sentence" to "recall"/"complete", never
        visiting "feedback" — see data-model.md's state-machine table."""
        self.pending_undo = None
        if self.step != "sentence":
            raise WrongStepError("not awaiting a sentence")

        append_attempt(self.progress_file, PracticeAttempt(**self.pending_attempt))
        self._advance_after_attempt(self.pending_attempt["correct"])

    def _advance_after_attempt(self, correct: bool) -> None:
        """Shared tail for finalizing a completed item (spec 006's
        skip_sentence, continue_to_next, and spec 012's recall-only
        submit_answer): tally if correct, clear the pending attempt/
        correction, advance to the next item or "complete"."""
        if correct:
            self.correct_count += 1

        self.pending_attempt = None
        self.last_correction = None
        self.current_index += 1
        self.step = "complete" if self.current_index >= len(self.items) else "recall"

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
        if self.group_locked or self.step not in ("recall", "sentence", "feedback", "reveal"):
            raise WrongStepError("no session to end")

        self.pending_attempt = None
        self.last_correction = None
        items, warnings = self._load(self.vocab_dir)
        self.warnings = warnings
        self.all_items = items
        self.step = "choose" if self.all_items else "empty"

    def retry_sentence(self) -> None:
        """Go back from "feedback" to "sentence" for the same word
        (Broadsheet redesign's "Try another sentence"). The reviewed
        sentence stays in the progress log; the next one is logged too."""
        self.pending_undo = None
        if self.step != "feedback":
            raise WrongStepError("no sentence feedback to retry")

        self.pending_attempt.pop("sentence", None)
        self.pending_attempt.pop("feedback", None)
        self.last_correction = None
        self.step = "sentence"

    def continue_to_next(self) -> None:
        self.pending_undo = None
        if self.step == "complete":
            return
        if self.step == "reveal":
            # Recall-only, incorrect (spec 013): the attempt was held,
            # unrecorded, at submit_answer() time — record it now, the
            # moment the learner is done reviewing it.
            append_attempt(self.progress_file, PracticeAttempt(**self.pending_attempt))
            self._advance_after_attempt(self.pending_attempt["correct"])
            return
        if self.step != "feedback":
            raise WrongStepError("not ready to continue")

        self._advance_after_attempt(self.pending_attempt["correct"])

    def remove_current(self, remove_fn) -> dict:
        """Take the current word out of practice for good (spec 020).
        *remove_fn(item)* deletes it from its file (or hides it) and
        returns what undo needs; it runs first, so a failure leaves the
        session as it was. An attempt already made is logged as on
        continue/skip; at recall nothing was answered, so nothing is."""
        if self.step not in ("recall", "reveal", "sentence"):
            raise WrongStepError("no word to remove")
        item = self.current_item
        token = remove_fn(item)

        if self.step in ("reveal", "sentence"):
            append_attempt(self.progress_file, PracticeAttempt(**self.pending_attempt))
            if self.pending_attempt["correct"]:
                self.correct_count += 1
        self.pending_attempt = None
        self.last_correction = None

        index = self.current_index
        del self.items[index]
        all_index = None
        if self.all_items is not self.items:  # a locked session shares one list
            all_index = next(i for i, other in enumerate(self.all_items) if other is item)
            del self.all_items[all_index]
        self.step = "complete" if self.current_index >= len(self.items) else "recall"
        self.pending_undo = {"item": item, "index": index, "all_index": all_index, "token": token}
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

        if self.step in ("sentence", "feedback", "reveal"):
            base["accepted_expressions"] = item.accepted_expressions()
            # Revealed with the answer, never during recall (spec 017).
            base["ipa"] = item.ipa
            base["answer"] = self.pending_attempt["answer"]
            base["correct"] = self.pending_attempt["correct"]

        if self.step == "feedback":
            base["sentence"] = self.pending_attempt["sentence"]
            base["feedback"] = {
                "available": self.last_correction.available,
                "uses_expression": self.last_correction.uses_expression,
                "needs_correction": self.last_correction.needs_correction,
                "corrected": self.last_correction.corrected,
                "explanation": self.last_correction.explanation,
            }

        return base
