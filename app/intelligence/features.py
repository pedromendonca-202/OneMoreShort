"""Turn a production row (script, storyboard, metadata, snapshots, retention) into a feature vector."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.intelligence.schemas import VideoOutcome


def _latest(snapshots: list[Any]):
    return max(snapshots, key=lambda s: (s.age_minutes or 0, s.captured_at or datetime.min.replace(tzinfo=UTC))) if snapshots else None


def _at_24h(snapshots: list[Any]):
    candidates = [s for s in snapshots if (s.schedule_slot_min or 0) >= 1440 or (s.age_minutes or 0) >= 1440]
    return min(candidates, key=lambda s: s.age_minutes or 0) if candidates else None


def extract_features(production: Any) -> VideoOutcome:
    topic = next((t for t in getattr(production, "topics", []) if getattr(t, "selected", False)), None)
    script = getattr(production, "script", None)
    data = (script.data if script is not None else {}) or {}
    storyboard = getattr(production, "storyboard", None)
    meta = getattr(production, "video_metadata", None)
    upload = getattr(production, "upload", None)
    snapshots = list(getattr(production, "snapshots", []) or [])
    latest = _latest(snapshots)
    at_24h = _at_24h(snapshots)
    curves = list(getattr(production, "retention_curves", []) or [])
    curve = curves[-1] if curves else None
    analysis = (curve.analysis if curve is not None else {}) or {}

    duration = float(data.get("est_duration_s") or (script.est_duration_s if script else 0) or 0)
    words = int(data.get("total_words") or (script.total_words if script else 0) or 0)
    views = float(latest.views if latest else 0)
    likes = float(latest.likes if latest else 0)
    comments = float(latest.comments if latest else 0)
    shares = float((latest.shares if latest else 0) or 0)
    subs = float((latest.subscribers_gained if latest else 0) or 0)
    if latest is not None and latest.avg_view_pct is not None:
        retention = float(latest.avg_view_pct) / 100
    else:
        retention = float(analysis.get("avg_pct") or 0)
    age_hours = max(1 / 60, (latest.age_minutes or 0) / 60) if latest else 0

    narrator = next((a.voice for a in getattr(production, "audio_assets", []) if a.kind == "narration_beat" and a.voice), "") or ""
    caption = getattr(production, "caption", None)
    caption_style = ((caption.style or {}).get("font") if caption is not None and caption.style else "") or ""
    beats = data.get("beats") or []
    structure = "-".join(dict.fromkeys(str(beat.get("purpose", "")) for beat in beats)) if beats else ""
    published = getattr(upload, "published_at", None) or getattr(upload, "uploaded_at", None)

    return VideoOutcome(
        production_id=getattr(production, "id", "") or "",
        title=(meta.title if meta is not None else data.get("title_working", "")) or "",
        topic=getattr(topic, "topic", "") or "",
        category=(getattr(topic, "category", None) or "general"),
        hook_type=str(data.get("hook_type") or (script.hook_type if script else "") or "curiosity"),
        narrative_structure=structure,
        ending_type=str(data.get("ending_type") or (script.ending_type if script else "") or ""),
        loop_used=bool(data.get("loop_used", False)),
        cta_used=bool(data.get("cta_used", False)),
        duration_s=duration,
        scene_count=len((storyboard.data or {}).get("segments") or []) if storyboard is not None else 0,
        words=words,
        pacing_wps=round(words / duration, 3) if duration > 0 else 0,
        visual_style=(storyboard.visual_style if storyboard is not None else "") or "",
        narrator=narrator,
        caption_style=caption_style,
        published_at=published.isoformat() if published else None,
        views=views,
        views_24h=float(at_24h.views) if at_24h else 0,
        views_per_hour=round(views / age_hours, 3) if age_hours else 0,
        retention=round(retention, 4),
        completion=float(analysis.get("completion_est") or 0),
        engagement=round((likes + comments + shares) / views, 5) if views else 0,
        like_rate=round(likes / views, 5) if views else 0,
        share_rate=round(shares / views, 5) if views else 0,
        sub_conversion=round(subs / views, 5) if views else 0,
        drop_offs=[float(drop.get("t_s", 0)) for drop in analysis.get("drops") or []],
    )
