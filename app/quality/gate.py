"""Non-negotiable mechanical and policy checks before a video becomes READY."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from pydantic import BaseModel, Field

from app.audio.schemas import NarrationPlan
from app.editing.probe import probe
from app.metadata.generator import policy_check
from app.metadata.schemas import VideoMetadata
from app.veo.schemas import SegmentRecord


class Check(BaseModel):
    name: str
    passed: bool
    detail: str


class QualityReport(BaseModel):
    checks: list[Check] = Field(default_factory=list)
    passed: bool
    failed_stage_hint: str | None = None


def _value(cfg: Any, section: str, field: str, default: Any) -> Any:
    return getattr(getattr(cfg, section, cfg), field, default)


def run_quality_gate(
    final: Path | str,
    segments: Iterable[SegmentRecord | Any],
    narration: NarrationPlan,
    captions: Path | str | None,
    metadata: VideoMetadata,
    continuity_scores: Iterable[float | None],
    policy_llm,
    cfg: Any,
) -> QualityReport:
    info = probe(final)
    checks: list[Check] = []
    max_duration = float(_value(cfg, "video", "max_duration_s", 40))
    checks.append(Check(name="duration", passed=info.duration_s <= max_duration + 0.05,
                        detail=f"{info.duration_s:.2f}s (maximum {max_duration:.2f}s)"))
    target_w, target_h = int(_value(cfg, "video", "width", 1080)), int(_value(cfg, "video", "height", 1920))
    checks.append(Check(name="resolution", passed=(info.width, info.height) == (target_w, target_h),
                        detail=f"{info.width}x{info.height} (expected {target_w}x{target_h})"))
    checks.append(Check(name="fps", passed=info.fps is not None and 24 <= info.fps <= 30,
                        detail=f"{info.fps or 0:.3f} fps"))
    checks.append(Check(name="codecs", passed=info.vcodec == "h264" and info.acodec == "aac",
                        detail=f"video={info.vcodec}, audio={info.acodec}"))
    checks.append(Check(name="audio", passed=info.has_audio and narration.total_s > 0,
                        detail=f"audio={info.has_audio}, narration={narration.total_s:.2f}s"))
    items = list(segments)
    if items:
        checks.append(Check(name="segments", passed=len(items) == 5 and all(getattr(item, "status", "") == "validated" for item in items),
                            detail=f"{len(items)} validated segments"))
    if captions is not None:
        caption_file = Path(captions)
        checks.append(Check(name="captions", passed=caption_file.is_file() and caption_file.stat().st_size > 0,
                            detail=str(caption_file)))
    threshold = float(_value(cfg, "veo", "continuity_min_score", 0.6))
    scores = [score for score in continuity_scores if score is not None]
    if scores:
        checks.append(Check(name="continuity", passed=min(scores) >= threshold,
                            detail=f"minimum {min(scores):.2f} (threshold {threshold:.2f})"))
    verdict = policy_check(policy_llm, _script_for_policy(narration), metadata)
    checks.append(Check(name="policy", passed=verdict.ok, detail="; ".join(verdict.reasons or verdict.flags or ["approved"])))
    passed = all(check.passed for check in checks)
    hint = "NEEDS_REVIEW" if not verdict.ok else (next((check.name for check in checks if not check.passed), None))
    return QualityReport(checks=checks, passed=passed, failed_stage_hint=hint)


def _script_for_policy(narration: NarrationPlan):
    """Adapt narration back into the tiny Script-shaped object policy_check needs."""
    from app.scripting.schemas import HookType, Script

    beats = [item.beat for item in narration.beats]
    if not beats:
        # Quality gates can run on partially produced artifacts. Supplying a
        # conservative placeholder keeps a policy refusal explicit rather than
        # crashing and bypassing the review state.
        from app.scripting.schemas import Beat
        beats = [Beat(index=1, start_s=0, end_s=0.1, purpose="hook", narration="No narration available")]
    return Script(title_working="Quality gate review", beats=beats, hook_type=HookType.CURIOSITY, ending_type="statement",
                  cta_used=False, loop_used=False, total_words=max(1, sum(len(beat.narration.split()) for beat in beats)),
                  est_duration_s=min(40, max(0.1, beats[-1].end_s)))
