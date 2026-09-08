"""Offline sine-wave TTS with deterministic word boundaries."""
from __future__ import annotations

import re
from pathlib import Path

from app.audio.schemas import TTSResult, WordTiming
from app.editing.ffmpeg import run_ffmpeg


class MockTTS:
    voice = "mock-en-US"

    def __init__(self, *, wpm: int = 165):
        self.wpm = wpm
        self.calls: list[str] = []

    def synthesize(self, text: str, out_wav: Path) -> TTSResult:
        words = re.findall(r"\b[\w'-]+\b", text)
        if not words:
            raise ValueError("cannot synthesize empty narration")
        self.calls.append(text)
        duration = max(0.08, len(words) / self.wpm * 60)
        out_wav.parent.mkdir(parents=True, exist_ok=True)
        run_ffmpeg(["-y", "-f", "lavfi", "-i", f"sine=frequency=220:sample_rate=48000:duration={duration:.3f}",
                    "-c:a", "pcm_s16le", str(out_wav)], cwd=out_wav.parent)
        step = duration / len(words)
        timings = [WordTiming(word=word, start_s=round(i * step, 4), end_s=round((i + 1) * step, 4)) for i, word in enumerate(words)]
        return TTSResult(path=out_wav, duration_s=duration, words=timings, cost_usd=0)
