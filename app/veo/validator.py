"""Mechanical validation before a generated segment is allowed into the chain."""
from __future__ import annotations

from pathlib import Path

from app.editing.probe import probe
from app.veo.schemas import ValidationReport


def validate_segment(
    path: Path | str,
    *,
    expect_seconds: float = 8,
    tolerance: float = 1.0,
    min_w: int = 720,
    orientation: str = "portrait",
    require_audio: bool = True,
) -> ValidationReport:
    media = probe(path)
    issues: list[str] = []
    if abs(media.duration_s - expect_seconds) > tolerance:
        issues.append(f"duration {media.duration_s:.2f}s is outside {expect_seconds:.2f}±{tolerance:.2f}s")
    if media.width is None or media.height is None:
        issues.append("video stream or dimensions are missing")
    elif media.width < min_w:
        issues.append(f"width {media.width}px is below minimum {min_w}px")
    elif orientation == "portrait" and media.height <= media.width:
        issues.append(f"expected portrait video, got {media.width}x{media.height}")
    if media.vcodec != "h264":
        issues.append(f"expected H.264 video, got {media.vcodec or 'none'}")
    if require_audio and not media.has_audio:
        issues.append("audio stream is missing")
    return ValidationReport(ok=not issues, issues=issues, media=media)
