"""Free Edge TTS adapter; word timing is unavailable in its saved-audio path."""
from __future__ import annotations

import asyncio
from pathlib import Path

from app.audio.schemas import TTSResult
from app.editing.ffmpeg import run_ffmpeg
from app.editing.probe import probe


class EdgeTTS:
    def __init__(self, voice: str = "en-US-GuyNeural"):
        self.voice = voice

    def synthesize(self, text: str, out_wav: Path) -> TTSResult:
        import edge_tts

        temp = out_wav.with_suffix(".edge.mp3")
        asyncio.run(edge_tts.Communicate(text, self.voice).save(str(temp)))
        try:
            out_wav.parent.mkdir(parents=True, exist_ok=True)
            run_ffmpeg(["-y", "-i", str(temp), "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", str(out_wav)], cwd=out_wav.parent)
        finally:
            temp.unlink(missing_ok=True)
        return TTSResult(path=out_wav, duration_s=probe(out_wav).duration_s, words=None, cost_usd=0)
