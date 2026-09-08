"""Join normalized segments without an unsafe shell command or filter path."""
from __future__ import annotations

import tempfile
from pathlib import Path

from app.editing.ffmpeg import run_ffmpeg


def _concat_entry(path: Path, cwd: Path) -> str:
    try:
        text = path.resolve().relative_to(cwd.resolve()).as_posix()
    except ValueError:
        text = path.resolve().as_posix()
    return "file '" + text.replace("'", "\\'") + "'\n"


def concat_segments(paths: list[Path | str], dst: Path | str) -> Path:
    if not paths:
        raise ValueError("at least one segment is required for concatenation")
    output = Path(dst).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    segments = [Path(path).resolve() for path in paths]
    missing = [str(path) for path in segments if not path.is_file()]
    if missing:
        raise FileNotFoundError(", ".join(missing))
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".txt", prefix="oms-concat-", dir=output.parent, delete=False, newline="\n") as listing:
        listing.writelines(_concat_entry(path, output.parent) for path in segments)
        list_path = Path(listing.name)
    try:
        run_ffmpeg([
            "-y", "-f", "concat", "-safe", "0", "-i", list_path.name, "-map", "0:v:0", "-map", "0:a?",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", output.name,
        ], cwd=output.parent)
    finally:
        list_path.unlink(missing_ok=True)
    return output
