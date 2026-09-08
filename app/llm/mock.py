"""Deterministic offline LLM: fills any Pydantic schema with valid values; supports per-schema/per-task handlers."""
from __future__ import annotations

import datetime as dt
import enum
import types
import typing
from pathlib import Path
from typing import Any, Callable, Union, get_args, get_origin

from annotated_types import Ge, Gt, Le, Lt, MaxLen, MinLen
from pydantic import BaseModel
from pydantic_core import PydanticUndefined

from app.llm.base import BaseLLM, LLMRequest, LLMResponse

Handler = Callable[[LLMRequest], Any]


def _bounds(metadata: list[Any]) -> dict[str, Any]:
    b: dict[str, Any] = {}
    for m in metadata:
        if isinstance(m, Ge):
            b["ge"] = m.ge
        elif isinstance(m, Gt):
            b["gt"] = m.gt
        elif isinstance(m, Le):
            b["le"] = m.le
        elif isinstance(m, Lt):
            b["lt"] = m.lt
        elif isinstance(m, MinLen):
            b["min_len"] = m.min_length
        elif isinstance(m, MaxLen):
            b["max_len"] = m.max_length
    return b


def _number(kind: type, b: dict[str, Any]) -> Any:
    lo = b.get("ge", b.get("gt"))
    hi = b.get("le", b.get("lt"))
    if lo is not None and hi is not None:
        val = (lo + hi) / 2
    elif lo is not None:
        val = lo + (1 if "gt" in b else 0) + (0 if kind is float else 1)
    elif hi is not None:
        val = hi - 1
    else:
        val = 0.5 if kind is float else 1
    return float(val) if kind is float else int(val)


def _value_for(annotation: Any, name: str, metadata: list[Any], depth: int) -> Any:
    origin = get_origin(annotation)
    args = get_args(annotation)
    b = _bounds(metadata)

    if origin in (Union, types.UnionType):
        non_none = [a for a in args if a is not type(None)]
        return _value_for(non_none[0], name, metadata, depth) if non_none else None
    if origin is typing.Literal:
        return args[0]
    if origin is typing.Annotated:
        return _value_for(args[0], name, list(args[1:]) + metadata, depth)
    if origin in (list, typing.List, set, frozenset, tuple):
        n = max(1, b.get("min_len", 1))
        inner = args[0] if args else str
        items = [_value_for(inner, f"{name}_{i + 1}", [], depth + 1) for i in range(n)]
        return tuple(items) if origin is tuple else items
    if origin in (dict, typing.Dict):
        return {}
    if annotation is Any:
        return f"mock {name}"
    if isinstance(annotation, type):
        if issubclass(annotation, BaseModel):
            return fill_model(annotation, depth + 1)
        if issubclass(annotation, enum.Enum):
            return list(annotation)[0]
        if annotation is bool:
            return True
        if annotation is int:
            return _number(int, b)
        if annotation is float:
            return _number(float, b)
        if annotation is str:
            text = f"mock {name.replace('_', ' ')}"
            if "min_len" in b and len(text) < b["min_len"]:
                text = (text + " ") * (b["min_len"] // len(text) + 1)
            if "max_len" in b:
                text = text[: b["max_len"]]
            return text
        if annotation is dt.datetime:
            return dt.datetime(2026, 9, 7, 12, 0, tzinfo=dt.timezone.utc)
        if annotation is dt.date:
            return dt.date(2026, 9, 7)
        if annotation is Path:
            return Path("mock")
    return f"mock {name}"


def fill_model(model_cls: type[BaseModel], depth: int = 0) -> BaseModel:
    """Build a valid instance of `model_cls` (required fields filled, defaults kept)."""
    if depth > 6:
        raise RecursionError("fill_model nesting too deep")
    data: dict[str, Any] = {}
    for name, field in model_cls.model_fields.items():
        if field.default is not PydanticUndefined or field.default_factory is not None:
            continue
        data[name] = _value_for(field.annotation, name, list(field.metadata), depth)
    return model_cls.model_validate(data)


def _mock_video_metadata(req: LLMRequest) -> dict[str, Any]:
    """VideoMetadata has cross-field rules (must include #Shorts) that generic filling cannot satisfy."""
    return {
        "title": "The Strange Reason This Works",
        "description": "A quick, source-aware explanation of a surprising fact. Generated in mock mode.",
        "hashtags": ["#Shorts", "#Science", "#OneMoreShort"],
        "tags": ["shorts", "science", "facts"],
        "category_id": "27",
        "pinned_comment": "Which part surprised you most?",
        "thumbnail_time_s": 1.5,
    }


DEFAULT_HANDLERS: dict[str, Handler] = {
    "VideoMetadata": _mock_video_metadata,
}


class MockLLM(BaseLLM):
    name = "mock"

    def __init__(self, handlers: dict[str, Handler] | None = None, default_text: str = "mock response"):
        super().__init__()
        self.handlers: dict[str, Handler] = {**DEFAULT_HANDLERS, **dict(handlers or {})}
        self.default_text = default_text
        self.calls: list[LLMRequest] = []

    def generate(self, req: LLMRequest) -> LLMResponse:
        self.calls.append(req)
        handler = None
        if req.response_model is not None:
            handler = self.handlers.get(req.response_model.__name__)
        if handler is None and req.task:
            handler = self.handlers.get(req.task)
        if req.response_model is not None:
            obj = handler(req) if handler else fill_model(req.response_model)
            if isinstance(obj, dict):
                obj = req.response_model.model_validate(obj)
            res = LLMResponse(text=obj.model_dump_json(), parsed=obj, model="mock")
        else:
            text = handler(req) if handler else self.default_text
            res = LLMResponse(text=str(text), model="mock")
        self._track(res)
        return res
