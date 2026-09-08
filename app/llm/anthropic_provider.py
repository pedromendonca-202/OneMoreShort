"""Anthropic provider (claude-opus-5 by default): structured outputs via output_config, web search tool, image input.

Adaptive thinking is the model default (no `thinking` parameter is sent). Server-side refusal fallbacks are not
enabled here; a `stop_reason == "refusal"` is surfaced as a non-retryable ExternalAPIError so the pipeline can route
the production to NEEDS_REVIEW instead of publishing something the model declined to write.
"""
from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from typing import Any

from app.core.cost import estimate_llm_cost
from app.core.errors import ExternalAPIError, RateLimited
from app.core.logging import get_logger
from app.core.retry import retrying
from app.llm.base import BaseLLM, LLMRequest, LLMResponse, parse_json_text


def _strict(schema: dict[str, Any]) -> dict[str, Any]:
    """Anthropic structured outputs require additionalProperties=false on every object."""
    if isinstance(schema, dict):
        if schema.get("type") == "object":
            schema.setdefault("additionalProperties", False)
        for v in schema.values():
            if isinstance(v, dict):
                _strict(v)
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        _strict(item)
    return schema


class AnthropicProvider(BaseLLM):
    name = "anthropic"

    def __init__(self, api_key: str | None, model: str = "claude-opus-5", timeout_s: int = 180, max_attempts: int = 5, max_output_tokens: int = 16000):
        super().__init__()
        self._api_key = api_key
        self._model = model
        self._timeout_s = timeout_s
        self._max_attempts = max_attempts
        self._max_output_tokens = max_output_tokens
        self._client = None
        self._log = get_logger(api="anthropic")

    def model_for(self, role: str) -> str:
        return self._model

    def _client_get(self):
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic(api_key=self._api_key, timeout=float(self._timeout_s), max_retries=0)
        return self._client

    @staticmethod
    def _image_block(img: Path | bytes) -> dict[str, Any]:
        if isinstance(img, (str, Path)):
            p = Path(img)
            data, mime = p.read_bytes(), mimetypes.guess_type(p.name)[0] or "image/png"
        else:
            data, mime = img, "image/png"
        return {"type": "image", "source": {"type": "base64", "media_type": mime, "data": base64.b64encode(data).decode()}}

    def generate(self, req: LLMRequest) -> LLMResponse:
        import anthropic

        content: list[dict[str, Any]] = [self._image_block(i) for i in req.images]
        content.append({"type": "text", "text": req.prompt})
        kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": req.max_output_tokens or self._max_output_tokens,
            "messages": [{"role": "user", "content": content}],
        }
        if req.system:
            kwargs["system"] = req.system
        if req.temperature is not None and req.temperature != 1.0 and not self._model.startswith(("claude-opus-5", "claude-sonnet-5", "claude-fable")):
            kwargs["temperature"] = req.temperature
        if req.response_model is not None:
            kwargs["output_config"] = {"format": {"type": "json_schema", "schema": _strict(req.response_model.model_json_schema())}}
        if req.use_search:
            kwargs["tools"] = [{"type": "web_search_20260209", "name": "web_search", "max_uses": 5}]

        @retrying("anthropic", max_attempts=self._max_attempts, wait_initial=2, wait_max=60, exceptions=(RateLimited, ExternalAPIError))
        def _do():
            try:
                return self._client_get().messages.create(**kwargs)
            except anthropic.RateLimitError as exc:
                raise RateLimited("anthropic", str(exc)[:300]) from exc
            except anthropic.APIStatusError as exc:
                retryable = exc.status_code >= 500 or exc.status_code in (408, 409)
                raise ExternalAPIError("anthropic", str(exc)[:300], retryable=retryable) from exc
            except anthropic.APIConnectionError as exc:
                raise ExternalAPIError("anthropic", str(exc)[:300], retryable=True) from exc

        resp = _do()
        if getattr(resp, "stop_reason", None) == "refusal":
            raise ExternalAPIError("anthropic", "model refused the request", retryable=False)
        text_parts: list[str] = []
        grounding: list[dict[str, Any]] = []
        for block in resp.content:
            btype = getattr(block, "type", "")
            if btype == "text":
                text_parts.append(block.text)
            elif btype == "web_search_tool_result":
                results = getattr(block, "content", None)
                if isinstance(results, list):
                    for r in results:
                        grounding.append({"uri": getattr(r, "url", None), "title": getattr(r, "title", None)})
        text = "".join(text_parts)
        usage = getattr(resp, "usage", None)
        in_tok = int(getattr(usage, "input_tokens", 0) or 0)
        out_tok = int(getattr(usage, "output_tokens", 0) or 0)
        out = LLMResponse(text=text, model=self._model, input_tokens=in_tok, output_tokens=out_tok, cost_usd=estimate_llm_cost(self._model, in_tok, out_tok), grounding=grounding)
        if req.response_model is not None:
            try:
                out.parsed = req.response_model.model_validate(parse_json_text(text))
            except Exception as exc:
                self._log.warning("anthropic_parse_failed", error=str(exc)[:300], task=req.task)
        self._track(out)
        return out
