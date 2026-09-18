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


@patch("src.services.llm_client.requests.post")
def test_request_uses_structured_format_and_default_model(mock_post):
    mock_post.return_value = _FakeResponse(
        200,
        _content(
            {
                "uses_expression": True,
                "needs_correction": False,
                "corrected": None,
                "explanation": None,
            }
        ),
    )
    request_correction("receive", "I received a gift.", base_url="http://localhost:11434")

    _, kwargs = mock_post.call_args
    payload = kwargs["json"]
    assert payload["model"] == "qwen3:14b"
    assert isinstance(payload["format"], dict)
    assert payload["format"]["type"] == "object"
    assert set(payload["format"]["required"]) == {
        "uses_expression",
        "needs_correction",
        "corrected",
        "explanation",
    }


@patch("src.services.llm_client.requests.post")
def test_model_name_is_configurable(mock_post):
    mock_post.return_value = _FakeResponse(
        200,
        _content(
            {
                "uses_expression": True,
                "needs_correction": False,
                "corrected": None,
                "explanation": None,
            }
        ),
    )
    request_correction("receive", "I received a gift.", base_url="http://localhost:11434", model="llama3.1")
    _, kwargs = mock_post.call_args
    assert kwargs["json"]["model"] == "llama3.1"


@patch("src.services.llm_client.requests.post")
def test_well_formed_reply_needs_correction(mock_post):
    mock_post.return_value = _FakeResponse(
        200,
        _content(
            {
                "uses_expression": True,
                "needs_correction": True,
                "corrected": "I received a gift yesterday.",
                "explanation": "Past tense is needed.",
            }
        ),
    )
    result = request_correction("receive", "I recieve a gift yesterday.", base_url="http://localhost:11434")
    assert result.available is True
    assert result.uses_expression is True
    assert result.needs_correction is True
    assert result.corrected == "I received a gift yesterday."
    assert result.explanation == "Past tense is needed."


@patch("src.services.llm_client.requests.post")
def test_well_formed_reply_already_correct(mock_post):
    mock_post.return_value = _FakeResponse(
        200,
        _content(
            {
                "uses_expression": True,
                "needs_correction": False,
                "corrected": None,
                "explanation": None,
            }
        ),
    )
    result = request_correction("receive", "I received a gift.", base_url="http://localhost:11434")
    assert result.available is True
    assert result.needs_correction is False


@patch("src.services.llm_client.requests.post")
def test_well_formed_reply_missing_expression(mock_post):
    mock_post.return_value = _FakeResponse(
        200,
        _content(
            {
                "uses_expression": False,
                "needs_correction": False,
                "corrected": None,
                "explanation": None,
            }
        ),
    )
    result = request_correction("receive", "I am happy today.", base_url="http://localhost:11434")
    assert result.available is True
    assert result.uses_expression is False


@patch("src.services.llm_client.requests.post")
def test_non_json_reply_is_treated_as_unavailable(mock_post):
    mock_post.return_value = _FakeResponse(200, _content("this is not JSON at all"))
    result = request_correction("receive", "I received a gift.", base_url="http://localhost:11434")
    assert result.available is False


@patch("src.services.llm_client.requests.post")
def test_json_missing_required_key_is_treated_as_unavailable(mock_post):
    mock_post.return_value = _FakeResponse(
        200,
        _content({"uses_expression": True, "needs_correction": False}),  # missing corrected/explanation
    )
    result = request_correction("receive", "I received a gift.", base_url="http://localhost:11434")
    assert result.available is False


@patch("src.services.llm_client.requests.post")
def test_json_with_wrong_field_type_is_treated_as_unavailable(mock_post):
    mock_post.return_value = _FakeResponse(
        200,
        _content(
            {
                "uses_expression": "yes",  # should be a boolean, not a string
                "needs_correction": False,
                "corrected": None,
                "explanation": None,
            }
        ),
    )
    result = request_correction("receive", "I received a gift.", base_url="http://localhost:11434")
    assert result.available is False


@patch("src.services.llm_client.requests.post")
def test_json_array_instead_of_object_is_treated_as_unavailable(mock_post):
    mock_post.return_value = _FakeResponse(200, _content("[1, 2, 3]"))
    result = request_correction("receive", "I received a gift.", base_url="http://localhost:11434")
    assert result.available is False


@patch("src.services.llm_client.requests.post")
def test_non_200_status_is_treated_as_unavailable(mock_post):
    mock_post.return_value = _FakeResponse(500, {})
    result = request_correction("receive", "I received a gift.", base_url="http://localhost:11434")
    assert result.available is False


@patch("src.services.llm_client.requests.post", side_effect=ConnectionError("refused"))
def test_connection_error_is_treated_as_unavailable(mock_post):
    result = request_correction("receive", "I received a gift.", base_url="http://localhost:11434")
    assert result.available is False
