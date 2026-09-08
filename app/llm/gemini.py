"""Gemini provider (google-genai): structured JSON output, Google Search grounding, image input, cost tracking."""
from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Any

from app.core.cost import GROUNDED_SEARCH_QUERY_USD, estimate_llm_cost
from app.core.errors import ExternalAPIError, RateLimited
from app.core.logging import get_logger
from app.core.retry import retrying
from app.llm.base import BaseLLM, LLMRequest, LLMResponse, parse_json_text


class GeminiProvider(BaseLLM):
    name = "gemini"

    def __init__(
        self,
        api_key: str,
        fast_model: str,
        smart_model: str,
        vision_model: str | None = None,
        timeout_s: int = 180,
        max_attempts: int = 5,
        default_temperature: float = 0.7,
        max_output_tokens: int = 8192,
    ):
        super().__init__()
        self._api_key = api_key
        self._models = {"fast": fast_model, "smart": smart_model, "vision": vision_model or fast_model}
        self._timeout_s = timeout_s
        self._max_attempts = max_attempts
        self._temperature = default_temperature
        self._max_output_tokens = max_output_tokens
        self._client = None
        self._log = get_logger(api="gemini")

    # --- public --------------------------------------------------------
    def model_for(self, role: str) -> str:
        return self._models.get(role, self._models["fast"])

    def generate(self, req: LLMRequest) -> LLMResponse:
        role = "vision" if req.images and req.role == "fast" else req.role
        model = self.model_for(role)
        contents = self._contents(req)

        if req.use_search and req.response_model is not None:
            # Grounded call returns prose; a second cheap call structures it (search + JSON mode can't be combined).
            grounded = self._call(model, contents, self._config(req, structured=False, search=True))
            out1 = self._to_llm_response(grounded, model)
            self._track(out1)
            structure_req = req.model_copy(update={
                "prompt": f"Convert the following research notes into the required JSON schema. Keep every fact and its source URL.\n\n{out1.text}",
                "use_search": False, "images": [], "role": "fast",
            })
            fast_model = self.model_for("fast")
            resp = self._call(fast_model, self._contents(structure_req), self._config(structure_req, structured=True, search=False))
            out = self._to_llm_response(resp, fast_model)
            out.grounding = out1.grounding
        else:
            resp = self._call(model, contents, self._config(req, structured=req.response_model is not None, search=req.use_search))
            out = self._to_llm_response(resp, model)

        if req.response_model is not None:
            try:
                out.parsed = req.response_model.model_validate(parse_json_text(out.text))
            except Exception as exc:  # leave parsed=None; structured() will repair
                self._log.warning("gemini_parse_failed", error=str(exc)[:300], task=req.task)
        self._track(out)
        return out

    # --- internals -----------------------------------------------------
    def _client_get(self):
        if self._client is None:
            from google import genai
            from google.genai import types

            self._client = genai.Client(api_key=self._api_key, http_options=types.HttpOptions(timeout=self._timeout_s * 1000))
        return self._client

    @staticmethod
    def _image_part(img: Path | bytes):
        from google.genai import types

        if isinstance(img, (str, Path)):
            p = Path(img)
            mime = mimetypes.guess_type(p.name)[0] or "image/png"
            return types.Part.from_bytes(data=p.read_bytes(), mime_type=mime)
        return types.Part.from_bytes(data=img, mime_type="image/png")

    def _contents(self, req: LLMRequest) -> list[Any]:
        from google.genai import types

        parts = [self._image_part(i) for i in req.images]
        parts.append(types.Part.from_text(text=req.prompt))
        return parts

    def _config(self, req: LLMRequest, *, structured: bool, search: bool):
        from google.genai import types

        kwargs: dict[str, Any] = {
            "temperature": req.temperature if req.temperature is not None else self._temperature,
            "max_output_tokens": req.max_output_tokens or self._max_output_tokens,
        }
        if req.system:
            kwargs["system_instruction"] = req.system
        if structured and req.response_model is not None:
            kwargs["response_mime_type"] = "application/json"
            kwargs["response_json_schema"] = req.response_model.model_json_schema()
        if search:
            kwargs["tools"] = [types.Tool(google_search=types.GoogleSearch())]
        return types.GenerateContentConfig(**kwargs)

    def _call(self, model: str, contents: list[Any], config):
        from google.genai import errors as genai_errors

        @retrying("gemini", max_attempts=self._max_attempts, wait_initial=2, wait_max=60, exceptions=(RateLimited, ExternalAPIError))
        def _do():
            try:
                return self._client_get().models.generate_content(model=model, contents=contents, config=config)
            except genai_errors.APIError as exc:
                code = getattr(exc, "code", None)
                if code in (429,):
                    raise RateLimited("gemini", str(exc)[:300]) from exc
                if code in (500, 502, 503, 504):
                    raise ExternalAPIError("gemini", str(exc)[:300], retryable=True) from exc
                raise ExternalAPIError("gemini", str(exc)[:300], retryable=False) from exc

        try:
            return _do()
        except ExternalAPIError as exc:
            if not exc.retryable:
                raise
            raise

    def _to_llm_response(self, resp: Any, model: str) -> LLMResponse:
        try:
            text = resp.text or ""
        except Exception:
            text = ""
        usage = getattr(resp, "usage_metadata", None)
        in_tok = int(getattr(usage, "prompt_token_count", 0) or 0)
        out_tok = int(getattr(usage, "candidates_token_count", 0) or 0) + int(getattr(usage, "thoughts_token_count", 0) or 0)
        grounding: list[dict[str, Any]] = []
        queries: list[str] = []
        cands = getattr(resp, "candidates", None) or []
        gm = getattr(cands[0], "grounding_metadata", None) if cands else None
        if gm is not None:
            for ch in getattr(gm, "grounding_chunks", None) or []:
                web = getattr(ch, "web", None)
                if web is not None:
                    grounding.append({"uri": getattr(web, "uri", None), "title": getattr(web, "title", None)})
            queries = list(getattr(gm, "web_search_queries", None) or [])
        cost = estimate_llm_cost(model, in_tok, out_tok) + GROUNDED_SEARCH_QUERY_USD * len(queries)
        return LLMResponse(text=text, model=model, input_tokens=in_tok, output_tokens=out_tok, cost_usd=round(cost, 6), grounding=grounding)
