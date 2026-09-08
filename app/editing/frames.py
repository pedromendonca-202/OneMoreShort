"""Still-frame extraction for Veo conditioning and continuity checks."""
from __future__ import annotations

from pathlib import Path

from app.editing.ffmpeg import run_ffmpeg


def _extract(video: Path | str, out_png: Path | str, *, time_args: list[str]) -> Path:
    src, out = Path(video).resolve(), Path(out_png).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    run_ffmpeg(["-y", *time_args, "-i", str(src), "-map", "0:v:0", "-frames:v", "1", str(out)], cwd=out.parent)
    if not out.is_file() or out.stat().st_size == 0:
        raise RuntimeError(f"ffmpeg did not create extracted frame: {out}")
    return out


def extract_frame_at(video: Path | str, t: float, out_png: Path | str) -> Path:
    if t < 0:
        raise ValueError("frame time cannot be negative")
    return _extract(video, out_png, time_args=["-ss", f"{t:.3f}"])


def extract_first_frame(video: Path | str, out_png: Path | str) -> Path:
    return _extract(video, out_png, time_args=[])


def extract_last_frame(video: Path | str, out_png: Path | str) -> Path:
    # Seeking from EOF avoids needing an extra probe before every segment.
    return _extract(video, out_png, time_args=["-sseof", "-0.050"])
