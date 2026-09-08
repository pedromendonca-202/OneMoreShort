"""Thumbnails: one JPEG per production in storage/thumbs/<id>.jpg, extracted with ffmpeg."""
from __future__ import annotations

import re
from pathlib import Path

from app.core.logging import get_logger

log = get_logger(component="web.thumbs")
_ID = re.compile(r"^OMS-\d{8}-\d{4}$")


def thumbs_dir(ctx) -> Path:
    folder = ctx.orchestrator.storage.root / "thumbs"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _source_video(ctx, production_id: str) -> tuple[Path | None, float, bool]:
    """(video, time, is_final): the final render wins; otherwise the first clip of scene 1."""
    from app.core.db import session_scope
    from app.core.models import Production

    with session_scope(ctx.orchestrator.engine) as session:
        production = session.get(Production, production_id)
        if production is None:
            return None, 1.0, False
        if production.final_video and Path(production.final_video.path).is_file():
            at = production.video_metadata.thumbnail_time_s if production.video_metadata and production.video_metadata.thumbnail_time_s else 1.0
            return Path(production.final_video.path), float(at), True
        for segment in production.segments:
            if segment.index == 1 and segment.file_path and Path(segment.file_path).is_file():
                return Path(segment.file_path), 0.0, False
    inbox = ctx.orchestrator.storage.dir_for(production_id, "manual_input")
    accepted = {ext.lower() for ext in ctx.settings.generation.accepted_extensions}
    clips = sorted(p for p in inbox.iterdir() if p.is_file() and p.suffix.lower() in accepted)
    return (clips[0], 0.0, False) if clips else (None, 1.0, False)


def clip_thumbnail(ctx, production_id: str, scene: int) -> Path | None:
    """First frame of the clip uploaded for one scene (storage/thumbs/<id>_clipN.jpg)."""
    if not _ID.match(production_id) or scene not in range(1, 6):
        return None
    from app.web.queries import inbox_clips
    from app.core.db import session_scope
    from app.core.models import Production

    with session_scope(ctx.orchestrator.engine) as session:
        production = session.get(Production, production_id)
        if production is None:
            return None
        clip = next((c for c in inbox_clips(ctx, production) if c["scene"] == scene), None)
    if clip is None or not clip.get("file"):
        return None
    source = ctx.orchestrator.storage.dir_for(production_id, "manual_input") / clip["file"]
    out = thumbs_dir(ctx) / f"{production_id}_clip{scene}.jpg"
    if out.is_file() and out.stat().st_mtime >= source.stat().st_mtime:
        return out
    try:
        from app.editing.frames import extract_frame_at

        extract_frame_at(source, 0.2, out)
    except Exception as err:
        log.warning("thumb.clip_failed", production_id=production_id, scene=scene, error=str(err)[:300])
        return None
    return out


def thumbnail_for(ctx, production_id: str, *, refresh: bool = False) -> Path | None:
    """Return the JPEG for a production, generating it when a video exists. None when nothing to show."""
    if not _ID.match(production_id):
        return None
    out = thumbs_dir(ctx) / f"{production_id}.jpg"
    source, at, is_final = _source_video(ctx, production_id)
    if source is None:
        return out if out.is_file() else None
    if out.is_file() and not refresh and (not is_final or out.stat().st_mtime >= source.stat().st_mtime):
        # A clip-based thumbnail is only a placeholder: never overwrite an existing image with it.
        return out
    try:
        from app.editing.frames import extract_frame_at

        extract_frame_at(source, at, out)
    except Exception as err:
        log.warning("thumb.failed", production_id=production_id, error=str(err)[:300])
        return out if out.is_file() else None
    return out
