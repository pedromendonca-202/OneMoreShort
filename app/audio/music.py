"""Select operator-provided licensed music; none is bundled by the project."""
from __future__ import annotations

from pathlib import Path


def choose_music(directory: Path | str) -> Path | None:
    root = Path(directory)
    tracks = [path for path in sorted(root.glob("*")) if path.suffix.lower() in {".mp3", ".wav", ".m4a", ".aac"}]
    return tracks[0] if tracks else None
