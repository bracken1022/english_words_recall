"""Exact-match grading of a learner's recall answer (FR-004)."""

from src.models.vocabulary_item import VocabularyItem


def grade_answer(item: VocabularyItem, answer: str) -> bool:
    """Case-insensitive, whitespace-tolerant exact match; no fuzzy tolerance."""
    normalized_answer = answer.strip().casefold()
    if not normalized_answer:
        return False
    accepted = {expr.strip().casefold() for expr in item.accepted_expressions()}
    return normalized_answer in accepted
