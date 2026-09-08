"""Normalize arbitrary Veo output into editing-safe portrait H.264/AAC."""
from __future__ import annotations

from pathlib import Path

from app.editing.ffmpeg import run_ffmpeg


def normalize_segment(src: Path | str, dst: Path | str, *, w: int = 1080, h: int = 1920, fps: int = 24) -> Path:
    source, output = Path(src).resolve(), Path(dst).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1,fps={fps},format=yuv420p"
    run_ffmpeg([
        "-y", "-i", str(source), "-map", "0:v:0", "-map", "0:a?", "-vf", vf,
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(output),
    ], cwd=output.parent)
    return output
