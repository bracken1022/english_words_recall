"""Compare a sentence-recall attempt with the real sentence, word by word
(spec 022, FR-012, contracts/word-diff.md).

The result only guides the learner: it shows which words of the sentence
are missing from the attempt and which words of the attempt are extra.
The learner still marks "Got it" / "Not yet" themselves. Capital letters
and punctuation are ignored; contractions, digits and spelling variants
count as different words (accepted limits, research R4)."""

import difflib
from dataclasses import asdict, dataclass

_APOSTROPHES = str.maketrans({"’": "'", "‘": "'"})


@dataclass(frozen=True)
class WordMark:
    word: str  # as written, with its punctuation
    status: str  # "same" | "missing" | "extra"


@dataclass(frozen=True)
class AttemptComparison:
    sentence: list[WordMark]  # each "same" or "missing"
    attempt: list[WordMark]  # each "same" or "extra"

    def to_json(self) -> dict:
        return {
            "sentence": [asdict(m) for m in self.sentence],
            "attempt": [asdict(m) for m in self.attempt],
        }


def _normalise(word: str) -> str:
    """Lower case, straight apostrophes, outer punctuation stripped; inner
    apostrophes and hyphens kept ("Don't," -> "don't")."""
    word = word.lower().translate(_APOSTROPHES)
    start, end = 0, len(word)
    while start < end and not word[start].isalnum():
        start += 1
    while end > start and not word[end - 1].isalnum():
        end -= 1
    return word[start:end]


def _words(text: str) -> list[tuple[str, str]]:
    """(as written, normalised) for each word; punctuation-only words are
    dropped."""
    pairs = ((word, _normalise(word)) for word in text.split())
    return [(word, key) for word, key in pairs if key]


def compare(attempt: str, sentence: str) -> AttemptComparison | None:
    """Which words differ; None when the attempt is blank."""
    tried = _words(attempt)
    if not tried:
        return None
    real = _words(sentence)

    matcher = difflib.SequenceMatcher(
        None, [key for _, key in real], [key for _, key in tried], autojunk=False
    )
    real_same: set[int] = set()
    tried_same: set[int] = set()
    for block in matcher.get_matching_blocks():
        real_same.update(range(block.a, block.a + block.size))
        tried_same.update(range(block.b, block.b + block.size))

    return AttemptComparison(
        sentence=[
            WordMark(word, "same" if i in real_same else "missing")
            for i, (word, _) in enumerate(real)
        ],
        attempt=[
            WordMark(word, "same" if i in tried_same else "extra")
            for i, (word, _) in enumerate(tried)
        ],
    )
