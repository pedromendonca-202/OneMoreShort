"""Burn ASS captions and mux the final single audio track."""
from __future__ import annotations

from pathlib import Path

from app.core.storage import Storage
from app.editing.ffmpeg import run_ffmpeg


def _subtitles_filter(ass: Path, cwd: Path) -> str:
    relative = Storage.relpath(ass, cwd).replace("\\", "/")
    # The value is relative to cwd, avoiding Windows drive-colon/OneDrive path
    # failures in ffmpeg's subtitles filter parser.
    escaped = relative.replace("'", r"\'").replace(":", r"\:")
    return f"subtitles=filename='{escaped}':charenc=UTF-8"


def render_final(
    concat_video: Path | str,
    mixed_audio: Path | str,
    ass_path: Path | str,
    logo: Path | None,
    out_mp4: Path | str,
    max_duration_s: float,
    cwd: Path | str,
) -> Path:
    workdir = Path(cwd).resolve()
    video, audio, ass, output = Path(concat_video).resolve(), Path(mixed_audio).resolve(), Path(ass_path).resolve(), Path(out_mp4).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    args = ["-y", "-i", str(video), "-i", str(audio)]
    if logo:
        args += ["-loop", "1", "-i", str(Path(logo).resolve()), "-filter_complex",
                 f"[0:v]{_subtitles_filter(ass, workdir)}[captioned];[2:v]scale=140:-1[logo];[captioned][logo]overlay=W-w-40:40:shortest=1[v]",
                 "-map", "[v]"]
    else:
        args += ["-vf", _subtitles_filter(ass, workdir), "-map", "0:v:0"]
    args += ["-map", "1:a:0", "-t", f"{max_duration_s:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
             "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(output)]
    run_ffmpeg(args, cwd=workdir)
    return output
