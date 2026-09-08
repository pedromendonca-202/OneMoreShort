"""Provider-agnostic LLM interface with structured (Pydantic) outputs."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Literal, Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, ValidationError

T = TypeVar("T", bound=BaseModel)


class LLMRequest(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    prompt: str
    system: str | None = None
    response_model: type[BaseModel] | None = None
    images: list[Path | bytes] = Field(default_factory=list)
    use_search: bool = False
    temperature: float | None = None
    max_output_tokens: int | None = None
    role: Literal["fast", "smart", "vision"] = "fast"
    task: str = ""


class LLMResponse(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    text: str
    parsed: Any = None
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    grounding: list[dict[str, Any]] = Field(default_factory=list)


@runtime_checkable
class LLMProvider(Protocol):
    name: str

    def generate(self, req: LLMRequest) -> LLMResponse: ...


class BaseLLM:
    """Cost accounting shared by real providers; the orchestrator drains it into the ledger."""

    name = "base"

    def __init__(self) -> None:
        self._cost_since_drain = 0.0
        self.total_cost_usd = 0.0
        self.call_count = 0

    def _track(self, res: LLMResponse) -> None:
        self._cost_since_drain += res.cost_usd
        self.total_cost_usd += res.cost_usd
        self.call_count += 1

    def drain_cost(self) -> float:
        c, self._cost_since_drain = self._cost_since_drain, 0.0
        return c


_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def parse_json_text(text: str) -> Any:
    """Parse JSON from model output, tolerating code fences and surrounding prose."""
    candidates: list[str] = []
    m = _FENCE_RE.search(text)
    if m:
        candidates.append(m.group(1))
    candidates.append(text)
    for start_ch, end_ch in (("{", "}"), ("[", "]")):
        s, e = text.find(start_ch), text.rfind(end_ch)
        if s != -1 and e > s:
            candidates.append(text[s : e + 1])
    for c in candidates:
        try:
            return json.loads(c.strip())
        except (json.JSONDecodeError, ValueError):
            continue
    raise ValueError(f"no JSON object found in model output: {text[:200]!r}")


def structured(llm: LLMProvider, req: LLMRequest, repair_attempts: int = 1) -> BaseModel:
    """Run a request expecting `req.response_model`; repair once by feeding validation errors back."""
    if req.response_model is None:
        raise ValueError("structured() requires req.response_model")
    model_cls = req.response_model
    res = llm.generate(req)
    last_error: Exception | None = None
    for attempt in range(repair_attempts + 1):
        if isinstance(res.parsed, model_cls):
            return res.parsed
        try:
            data = res.parsed if isinstance(res.parsed, (dict, list)) else parse_json_text(res.text)
            return model_cls.model_validate(data)
        except (ValueError, ValidationError) as exc:
            last_error = exc
        if attempt >= repair_attempts:
            break
        repair_prompt = (
            f"{req.prompt}\n\n---\nYour previous answer failed validation against the required JSON schema.\n"
            f"Validation error:\n{str(last_error)[:2000]}\n\nPrevious answer:\n{res.text[:4000]}\n\n"
            "Return ONLY a corrected JSON object that satisfies the schema. No prose, no code fences."
        )
        res = llm.generate(req.model_copy(update={"prompt": repair_prompt}))
    raise ValueError(f"structured output failed for {model_cls.__name__}: {last_error}")
