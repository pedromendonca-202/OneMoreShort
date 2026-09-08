"""Google Veo long-running-operation client."""
from __future__ import annotations

import time
from pathlib import Path

from app.core.cost import estimate_veo_cost
from app.core.errors import ExternalAPIError, RateLimited
from app.core.retry import retrying
from app.veo.schemas import VeoClient, VeoPrompt, VeoResult


class GoogleVeoClient:
    name = "veo"

    def __init__(self, api_key: str, model: str, resolution: str, poll_interval_s: float = 10, timeout_s: float = 900):
        self.api_key, self.model, self.resolution = api_key, model, resolution
        self.poll_interval_s, self.timeout_s = poll_interval_s, timeout_s
        self._client = None

    def _client_get(self):
        if self._client is None:
            from google import genai
            from google.genai import types

            self._client = genai.Client(api_key=self.api_key, http_options=types.HttpOptions(timeout=int(self.timeout_s * 1000)))
        return self._client

    def generate(self, prompt: VeoPrompt, out_path: Path) -> VeoResult:
        from google.genai import errors as genai_errors
        from google.genai import types

        config = types.GenerateVideosConfig(
            number_of_videos=1, duration_seconds=int(prompt.config.get("duration_seconds", 8)),
            aspect_ratio=str(prompt.config.get("aspect_ratio", "9:16")), resolution=self.resolution,
            person_generation=str(prompt.config.get("person_generation", "allow_adult")),
            generate_audio=bool(prompt.config.get("generate_audio", True)), negative_prompt=prompt.negative_prompt,
        )
        image = types.Image.from_file(location=str(prompt.first_frame)) if prompt.first_frame else None

        @retrying("veo", max_attempts=3, wait_initial=3, wait_max=60, exceptions=(RateLimited, ExternalAPIError))
        def create_and_wait():
            try:
                operation = self._client_get().models.generate_videos(model=self.model, prompt=prompt.prompt, image=image, config=config)
                started = time.monotonic()
                while not operation.done:
                    if time.monotonic() - started > self.timeout_s:
                        raise ExternalAPIError("veo", f"operation {getattr(operation, 'name', '?')} exceeded {self.timeout_s}s", retryable=True)
                    time.sleep(self.poll_interval_s)
                    operation = self._client_get().operations.get(operation)
                if getattr(operation, "error", None):
                    raise ExternalAPIError("veo", str(operation.error)[:500], retryable=False)
                return operation
            except genai_errors.APIError as exc:
                if getattr(exc, "code", None) == 429:
                    raise RateLimited("veo", str(exc)[:300]) from exc
                raise ExternalAPIError("veo", str(exc)[:300], retryable=getattr(exc, "code", 500) >= 500) from exc

        operation = create_and_wait()
        try:
            generated = operation.response.generated_videos[0].video
        except (AttributeError, IndexError, TypeError) as exc:
            raise ExternalAPIError("veo", "operation completed without a generated video", retryable=False) from exc
        out_path.parent.mkdir(parents=True, exist_ok=True)
        self._client_get().files.download(file=generated, destination=str(out_path))
        seconds = float(prompt.config.get("duration_seconds", 8))
        return VeoResult(path=out_path, operation_id=str(getattr(operation, "name", "")), seconds=seconds,
                         cost_usd=estimate_veo_cost(seconds, self.resolution), raw={"model": self.model})
