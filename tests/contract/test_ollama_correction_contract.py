"""Contract tests for contracts/ollama-correction-contract-delta.md (spec
010): request_correction() now makes a Judge call, then — only if the
Judge found a grammar or naturalness problem — a Teacher call. Every test
here mocks requests.post and inspects call_args_list rather than the
single last call, since there may now be up to two calls."""

import json
from unittest.mock import patch

from src.services.llm_client import request_correction


class _FakeResponse:
    def __init__(self, status_code: int, json_data: dict | None = None):
        self.status_code = status_code
        self._json_data = json_data or {}

    def json(self):
        return self._json_data


def _content(payload: dict | str) -> dict:
    text = payload if isinstance(payload, str) else json.dumps(payload)
    return {"message": {"role": "assistant", "content": text}}


def _judge_reply(uses_expression=True, grammatically_correct=True, natural=True):
    return _FakeResponse(
        200,
        _content(
            {
                "uses_expression": uses_expression,
                "grammatically_correct": grammatically_correct,
                "natural": natural,
            }
        ),
    )


def _teacher_reply(corrected="I received a gift yesterday.", explanation="Past tense is needed."):
    return _FakeResponse(200, _content({"corrected": corrected, "explanation": explanation}))


# --- Happy paths ---


@patch("src.services.llm_client.requests.post")
def test_already_correct_makes_only_judge_call(mock_post):
    mock_post.return_value = _judge_reply()
    result = request_correction("receive", "I received a gift.", base_url="http://localhost:11434")

    assert mock_post.call_count == 1
    payload = mock_post.call_args.kwargs["json"]
    assert payload["model"] == "qwen3:14b"
    assert set(payload["format"]["required"]) == {"uses_expression", "grammatically_correct", "natural"}

    assert result.available is True
    assert result.uses_expression is True
    assert result.needs_correction is False
    assert result.corrected is None
    assert result.explanation is None


@patch("src.services.llm_client.requests.post")
def test_grammar_problem_triggers_teacher_call(mock_post):
    mock_post.side_effect = [_judge_reply(grammatically_correct=False), _teacher_reply()]
    result = request_correction("receive", "I recieve a gift yesterday.", base_url="http://localhost:11434")

    assert mock_post.call_count == 2
    judge_payload = mock_post.call_args_list[0].kwargs["json"]
    teacher_payload = mock_post.call_args_list[1].kwargs["json"]
    assert set(judge_payload["format"]["required"]) == {"uses_expression", "grammatically_correct", "natural"}
    assert set(teacher_payload["format"]["required"]) == {"corrected", "explanation"}

    assert result.available is True
    assert result.needs_correction is True
    assert result.corrected == "I received a gift yesterday."
    assert result.explanation == "Past tense is needed."


@patch("src.services.llm_client.requests.post")
def test_unnatural_phrasing_alone_triggers_teacher_call(mock_post):
    mock_post.side_effect = [
        _judge_reply(natural=False),
        _teacher_reply(corrected="I got a gift.", explanation="More natural phrasing."),
    ]
    result = request_correction("receive", "I did receive of a gift.", base_url="http://localhost:11434")

    assert mock_post.call_count == 2
    assert result.needs_correction is True
    assert result.corrected == "I got a gift."


@patch("src.services.llm_client.requests.post")
def test_missing_target_expression_alone_does_not_trigger_teacher_call(mock_post):
    mock_post.return_value = _judge_reply(uses_expression=False)
    result = request_correction("receive", "I am happy today.", base_url="http://localhost:11434")

    assert mock_post.call_count == 1
    assert result.uses_expression is False
    assert result.needs_correction is False


@patch("src.services.llm_client.requests.post")
def test_missing_expression_and_grammar_problem_still_triggers_teacher_call(mock_post):
    """Combined case (quickstart.md #7): a missing target expression MUST
    NOT suppress the Teacher call when there's also a grammar problem —
    the two findings stay independent, matching today's existing
    behavior."""
    mock_post.side_effect = [
        _judge_reply(uses_expression=False, grammatically_correct=False),
        _teacher_reply(corrected="I am happy today.", explanation="Subject-verb agreement."),
    ]
    result = request_correction("receive", "I happy today.", base_url="http://localhost:11434")

    assert mock_post.call_count == 2
    assert result.uses_expression is False
    assert result.needs_correction is True


@patch("src.services.llm_client.requests.post")
def test_model_name_is_configurable_for_both_calls(mock_post):
    mock_post.side_effect = [_judge_reply(grammatically_correct=False), _teacher_reply()]
    request_correction("receive", "bad sentence", base_url="http://localhost:11434", model="llama3.1")

    assert mock_post.call_count == 2
    for call in mock_post.call_args_list:
        assert call.kwargs["json"]["model"] == "llama3.1"


# --- Judge-call failure modes: Teacher must never be invoked ---


@patch("src.services.llm_client.requests.post")
def test_judge_non_json_reply_is_unavailable(mock_post):
    mock_post.return_value = _FakeResponse(200, _content("this is not JSON at all"))
    result = request_correction("receive", "I received a gift.", base_url="http://localhost:11434")
    assert result.available is False
    assert mock_post.call_count == 1


@patch("src.services.llm_client.requests.post")
def test_judge_json_missing_required_key_is_unavailable(mock_post):
    mock_post.return_value = _FakeResponse(
        200, _content({"uses_expression": True, "grammatically_correct": True})  # missing "natural"
    )
    result = request_correction("receive", "I received a gift.", base_url="http://localhost:11434")
    assert result.available is False
    assert mock_post.call_count == 1


@patch("src.services.llm_client.requests.post")
def test_judge_json_wrong_field_type_is_unavailable(mock_post):
    mock_post.return_value = _FakeResponse(
        200,
        _content({"uses_expression": "yes", "grammatically_correct": True, "natural": True}),
    )
    result = request_correction("receive", "I received a gift.", base_url="http://localhost:11434")
    assert result.available is False
    assert mock_post.call_count == 1


@patch("src.services.llm_client.requests.post")
def test_judge_json_array_instead_of_object_is_unavailable(mock_post):
    mock_post.return_value = _FakeResponse(200, _content("[1, 2, 3]"))
    result = request_correction("receive", "I received a gift.", base_url="http://localhost:11434")
    assert result.available is False
    assert mock_post.call_count == 1


@patch("src.services.llm_client.requests.post")
def test_judge_non_200_status_is_unavailable(mock_post):
    mock_post.return_value = _FakeResponse(500, {})
    result = request_correction("receive", "I received a gift.", base_url="http://localhost:11434")
    assert result.available is False
    assert mock_post.call_count == 1


@patch("src.services.llm_client.requests.post", side_effect=ConnectionError("refused"))
def test_judge_connection_error_is_unavailable(mock_post):
    result = request_correction("receive", "I received a gift.", base_url="http://localhost:11434")
    assert result.available is False


# --- Teacher-call failure modes: whole result becomes unavailable, never partial ---


@patch("src.services.llm_client.requests.post")
def test_teacher_non_200_status_makes_whole_result_unavailable(mock_post):
    mock_post.side_effect = [_judge_reply(grammatically_correct=False), _FakeResponse(500, {})]
    result = request_correction("receive", "bad sentence", base_url="http://localhost:11434")
    assert result.available is False
    assert result.corrected is None
    assert result.explanation is None
    assert mock_post.call_count == 2


@patch("src.services.llm_client.requests.post")
def test_teacher_malformed_json_makes_whole_result_unavailable(mock_post):
    mock_post.side_effect = [
        _judge_reply(natural=False),
        _FakeResponse(200, _content({"corrected": "x"})),  # missing "explanation"
    ]
    result = request_correction("receive", "bad sentence", base_url="http://localhost:11434")
    assert result.available is False


@patch("src.services.llm_client.requests.post")
def test_teacher_connection_error_makes_whole_result_unavailable(mock_post):
    mock_post.side_effect = [_judge_reply(grammatically_correct=False), ConnectionError("refused")]
    result = request_correction("receive", "bad sentence", base_url="http://localhost:11434")
    assert result.available is False
