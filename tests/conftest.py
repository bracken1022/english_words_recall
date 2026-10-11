"""Shared test setup."""

import pytest
import requests


@pytest.fixture(autouse=True)
def _no_real_model(monkeypatch):
    """Spec 021 makes example sentences in the background whenever a word
    comes up, so any test could otherwise reach a real local model. Make
    it unreachable by default; a test that fakes the model patches
    requests.post itself, which overrides this."""

    def unreachable(*_args, **_kwargs):
        raise requests.ConnectionError("no model in tests")

    monkeypatch.setattr("src.services.llm_client.requests.post", unreachable)
