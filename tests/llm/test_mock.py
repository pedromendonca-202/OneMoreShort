from typing import Literal

from pydantic import BaseModel, Field

from app.llm.base import LLMRequest
from app.llm.mock import MockLLM, fill_model


class Inner(BaseModel):
    label: str
    weight: float = Field(ge=0, le=1)


class Outer(BaseModel):
    title: str
    count: int
    flag: bool
    kind: Literal["question", "shock"]
    items: list[Inner]
    optional_note: str | None = None


def test_fill_model_produces_valid_nested_instance():
    inst = fill_model(Outer)
    assert isinstance(inst, Outer)
    assert inst.kind in ("question", "shock")
    assert len(inst.items) >= 1 and 0 <= inst.items[0].weight <= 1


def test_mock_returns_parsed_object_for_schema():
    llm = MockLLM()
    res = llm.generate(LLMRequest(prompt="anything", response_model=Outer, task="test"))
    assert isinstance(res.parsed, Outer)
    assert res.cost_usd == 0
    assert llm.calls[0].task == "test"


def test_mock_handler_override_by_model_name():
    llm = MockLLM(handlers={"Outer": lambda req: Outer(title="custom", count=3, flag=False, kind="shock", items=[Inner(label="x", weight=0.2)])})
    res = llm.generate(LLMRequest(prompt="p", response_model=Outer))
    assert res.parsed.title == "custom"


def test_mock_text_response_without_schema():
    llm = MockLLM(default_text="hello")
    res = llm.generate(LLMRequest(prompt="p"))
    assert res.text == "hello" and res.parsed is None
