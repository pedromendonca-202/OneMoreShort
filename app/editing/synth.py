"""Generate tiny deterministic clips for mock mode and media tests."""
from __future__ import annotations

from pathlib import Path

from app.editing.ffmpeg import run_ffmpeg


def synth_segment(dst: Path | str, seconds: float, color: str, label: str, *, with_audio: bool = True) -> Path:
    if seconds <= 0:
        raise ValueError("synthetic segment duration must be positive")
    output = Path(dst).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    args = [
        "-y", "-f", "lavfi", "-i", f"color=c={color}:s=1080x1920:r=24:d={seconds:.3f}",
    ]
    if with_audio:
        args += ["-f", "lavfi", "-i", f"sine=frequency=440:sample_rate=48000:duration={seconds:.3f}", "-shortest"]
    args += [
        "-metadata", f"title={label}", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
    ]
    if with_audio:
        args += ["-c:a", "aac", "-b:a", "128k"]
    args += ["-movflags", "+faststart", str(output)]
    run_ffmpeg(args, cwd=output.parent)
    return output
