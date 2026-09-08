from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from app.audio.schemas import TTSResult


@runtime_checkable
class TTSProvider(Protocol):
    voice: str

    def synthesize(self, text: str, out_wav: Path) -> TTSResult: ...
