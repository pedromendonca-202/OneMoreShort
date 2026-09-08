import pytest
from pydantic import BaseModel

from app.llm.base import LLMRequest, LLMResponse, parse_json_text, structured


class Answer(BaseModel):
    value: int
    note: str


def test_parse_json_text_strips_fences_and_prose():
    text = 'Sure! Here you go:\n```json\n{"value": 3, "note": "ok"}\n```\nDone.'
    assert parse_json_text(text) == {"value": 3, "note": "ok"}


def test_parse_json_text_handles_arrays():
    assert parse_json_text("[1, 2, 3]") == [1, 2, 3]


class FlakyProvider:
    """Returns invalid JSON first, then valid: exercises the repair path."""

    name = "flaky"

    def __init__(self):
        self.calls = []

    def generate(self, req: LLMRequest) -> LLMResponse:
        self.calls.append(req)
        if len(self.calls) == 1:
            return LLMResponse(text='{"value": "not-an-int", "note": "x"}', model="flaky")
        return LLMResponse(text='{"value": 7, "note": "fixed"}', model="flaky")


def test_structured_repairs_once_and_returns_model():
    p = FlakyProvider()
    out = structured(p, LLMRequest(prompt="q", response_model=Answer))
    assert isinstance(out, Answer) and out.value == 7
    assert len(p.calls) == 2
    assert "validation" in p.calls[1].prompt.lower()


class AlwaysBad:
    name = "bad"

    def generate(self, req):
        return LLMResponse(text="nonsense", model="bad")


def test_structured_raises_after_repair_fails():
    with pytest.raises(ValueError):
        structured(AlwaysBad(), LLMRequest(prompt="q", response_model=Answer))
