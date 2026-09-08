"""Structured ffprobe metadata used by validation and quality gates."""
from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from app.editing.ffmpeg import run_ffprobe


class MediaInfo(BaseModel):
    duration_s: float
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    vcodec: str | None = None
    acodec: str | None = None
    has_audio: bool
    sample_rate: int | None = None
    size_bytes: int


def _rate(value: str | None) -> float | None:
    if not value or value == "0/0":
        return None
    try:
        numerator, denominator = value.split("/", 1)
        return float(numerator) / float(denominator)
    except (ValueError, ZeroDivisionError):
        return None


def probe(path: Path | str) -> MediaInfo:
    media = Path(path).resolve()
    if not media.is_file():
        raise FileNotFoundError(media)
    result = run_ffprobe([
        "-v", "error", "-show_entries", "format=duration", "-show_streams", "-of", "json", str(media),
    ], cwd=media.parent)
    data = json.loads(result.stdout)
    streams = data.get("streams") or []
    video = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    audio = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
    duration = float((data.get("format") or {}).get("duration") or 0)
    return MediaInfo(
        duration_s=duration,
        width=int(video["width"]) if video and video.get("width") else None,
        height=int(video["height"]) if video and video.get("height") else None,
        fps=_rate(video.get("avg_frame_rate")) if video else None,
        vcodec=video.get("codec_name") if video else None,
        acodec=audio.get("codec_name") if audio else None,
        has_audio=audio is not None,
        sample_rate=int(audio["sample_rate"]) if audio and audio.get("sample_rate") else None,
        size_bytes=media.stat().st_size,
    )
