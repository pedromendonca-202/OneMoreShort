"""Offline Veo adapter producing deterministic synthetic segments."""
from __future__ import annotations

from pathlib import Path

from app.core.cost import estimate_veo_cost
from app.editing.synth import synth_segment
from app.veo.schemas import VeoPrompt, VeoResult


class MockVeoClient:
    name = "mock_veo"

    def __init__(self, *, synth: bool = True, fail_segments: set[int] | None = None, crash_segments: set[int] | None = None):
        self.synth = synth
        self.fail_segments = fail_segments or set()
        self.crash_segments = crash_segments or set()
        self.calls: list[VeoPrompt] = []

    def generate(self, prompt: VeoPrompt, out_path: Path) -> VeoResult:
        self.calls.append(prompt)
        if prompt.segment in self.crash_segments:
            self.crash_segments.remove(prompt.segment)
            raise KeyboardInterrupt(f"simulated crash during mock Veo segment {prompt.segment}")
        if prompt.segment in self.fail_segments:
            raise RuntimeError(f"mock Veo failure at segment {prompt.segment}")
        seconds = float(prompt.config.get("duration_seconds", 8))
        resolution = str(prompt.config.get("resolution", "1080p"))
        if self.synth:
            colors = ["#1b1b1b", "#5f1111", "#111d5f", "#145f35", "#4c286e"]
            synth_segment(out_path, seconds, colors[(prompt.segment - 1) % len(colors)], f"mock Veo segment {prompt.segment}", with_audio=True)
        return VeoResult(path=out_path, operation_id=f"mock-veo-{prompt.segment:02d}-{len(self.calls):03d}", seconds=seconds,
                         cost_usd=estimate_veo_cost(seconds, resolution), raw={"mock": True})
