"""Resume-safe sequential Veo segment generation with continuity boundaries."""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.continuity.checker import check_continuity
from app.continuity.observer import observe_end_state
from app.continuity.schemas import ContinuityBible, SegmentEndState
from app.continuity.state import planned_end_state
from app.core.cost import Budget, estimate_veo_cost, record_cost
from app.core.errors import BudgetExceeded, ValidationFailed
from app.core.models import Prompt as PromptRow
from app.core.models import Segment as SegmentRow
from app.core.storage import Storage
from app.editing.frames import extract_first_frame, extract_last_frame
from app.llm.base import LLMProvider
from app.storyboard.schemas import Storyboard
from app.veo.prompt_builder import build_prompt
from app.veo.schemas import BrandStyle, SegmentRecord, VeoClient, VeoPrompt
from app.veo.validator import validate_segment


def _get(cfg: Any, section: str, name: str, default: Any) -> Any:
    return getattr(getattr(cfg, section, cfg), name, default)


def _brand(cfg: Any) -> BrandStyle:
    value = getattr(cfg, "brand", None)
    if value is None:
        return BrandStyle()
    dump = value.model_dump() if hasattr(value, "model_dump") else value
    return BrandStyle.model_validate(dump)


def _existing(session: Session, production_id: str, index: int) -> SegmentRow | None:
    return session.scalar(select(SegmentRow).where(SegmentRow.production_id == production_id, SegmentRow.index == index))


def _record_from_row(row: SegmentRow) -> SegmentRecord:
    if not row.file_path:
        raise RuntimeError(f"segment {row.index} has no stored file path")
    return SegmentRecord(
        index=row.index, status=row.status, path=Path(row.file_path),
        first_frame_path=Path(row.first_frame_path) if row.first_frame_path else None,
        last_frame_path=Path(row.last_frame_path) if row.last_frame_path else None,
        operation_id=row.operation_id, cost_usd=float(row.cost_usd or 0), continuity_score=row.continuity_score,
    )


def _observed_or_planned(row: SegmentRow | None, storyboard: Storyboard, bible: ContinuityBible, index: int) -> SegmentEndState | None:
    if row and row.observed_end_state:
        try:
            return SegmentEndState.model_validate(row.observed_end_state)
        except ValueError:
            pass
    if index <= 1:
        return None
    return planned_end_state(storyboard.segments[index - 2], bible)


def _store_prompt(session: Session, production_id: str, prompt: VeoPrompt, attempt: int) -> None:
    session.add(PromptRow(
        production_id=production_id, segment_index=prompt.segment, attempt=attempt, prompt=prompt.prompt,
        negative_prompt=prompt.negative_prompt, config=prompt.config, previous_end_state=prompt.previous_end_state,
        first_frame_path=str(prompt.first_frame) if prompt.first_frame else None,
    ))


def generate_segments(
    production_id: str,
    storyboard: Storyboard,
    bible: ContinuityBible,
    veo: VeoClient,
    llm: LLMProvider,
    storage: Storage,
    session: Session,
    cfg: Any,
) -> list[SegmentRecord]:
    """Generate one segment at a time, persisting each accepted boundary.

    Existing validated files are never regenerated. A process crash can therefore
    resume at its first incomplete segment without spending again on prior clips.
    """
    duration = float(_get(cfg, "veo", "duration_seconds", 8))
    resolution = str(_get(cfg, "veo", "resolution", "1080p"))
    max_attempts = int(_get(cfg, "limits", "max_video_generation_retries", 3))
    budget = Budget(float(_get(cfg, "limits", "daily_budget_usd", 10)))
    continuity_threshold = float(_get(cfg, "veo", "continuity_min_score", 0.6))
    observe = bool(_get(cfg, "veo", "observe_end_state", True))
    check = bool(_get(cfg, "veo", "check_continuity", True))
    brand = _brand(cfg)
    records: list[SegmentRecord] = []
    previous_row: SegmentRow | None = None

    for scene in storyboard.segments:
        index = scene.segment
        row = _existing(session, production_id, index)
        if row and row.status == "validated" and row.file_path and Path(row.file_path).is_file() and row.last_frame_path and Path(row.last_frame_path).is_file():
            records.append(_record_from_row(row))
            previous_row = row
            continue
        if row is None:
            row = SegmentRow(production_id=production_id, index=index, status="pending", attempts=0)
            session.add(row)
            session.flush()

        prior_state = _observed_or_planned(previous_row, storyboard, bible, index)
        previous_frame = Path(previous_row.last_frame_path) if previous_row and previous_row.last_frame_path else None
        last_error: Exception | None = None
        accepted = False
        for _ in range(int(row.attempts or 0), max_attempts):
            upcoming = estimate_veo_cost(duration, resolution)
            budget.check(session, datetime.now(UTC).date(), upcoming, raise_on_exceed=True)
            base_prompt = build_prompt(scene, bible, storyboard, prior_state, brand)
            prompt = base_prompt.model_copy(update={
                "first_frame": previous_frame,
                "config": {**base_prompt.config, "duration_seconds": duration, "resolution": resolution,
                           "aspect_ratio": _get(cfg, "veo", "aspect_ratio", "9:16"),
                           "generate_audio": _get(cfg, "veo", "generate_audio", True),
                           "person_generation": _get(cfg, "veo", "person_generation", "allow_adult")},
            })
            row.status, row.error = "generating", None
            row.attempts = int(row.attempts or 0) + 1
            _store_prompt(session, production_id, prompt, row.attempts)
            session.flush()  # persist the in-flight attempt for crash recovery
            output = storage.path_for(production_id, "segments", f"segment_{index:02d}.mp4")
            try:
                result = veo.generate(prompt, output)
                report = validate_segment(result.path, expect_seconds=duration, tolerance=max(0.25, min(1.0, duration * 0.20)))
                if not report.ok:
                    raise ValidationFailed(report.issues)
                first_frame = storage.path_for(production_id, "frames", f"segment_{index:02d}_first.png")
                last_frame = storage.path_for(production_id, "frames", f"segment_{index:02d}_last.png")
                extract_first_frame(result.path, first_frame)
                extract_last_frame(result.path, last_frame)
                observed = observe_end_state(llm, last_frame) if observe else planned_end_state(scene, bible)
                continuity_score = None
                if check and previous_frame:
                    checked = check_continuity(llm, previous_frame, first_frame)
                    continuity_score = checked.score
                    if checked.score < continuity_threshold:
                        raise ValidationFailed([f"continuity score {checked.score:.2f} below threshold {continuity_threshold:.2f}", *checked.issues])
                record_cost(session, production_id, api="veo", units=result.seconds,
                            unit_cost=estimate_veo_cost(1, resolution), usd=result.cost_usd,
                            note=f"segment {index}; operation {result.operation_id}")
                row.status, row.operation_id, row.file_path = "validated", result.operation_id, str(result.path)
                row.first_frame_path, row.last_frame_path = str(first_frame), str(last_frame)
                row.observed_end_state = observed.model_dump()
                row.continuity_score, row.continuity_issues = continuity_score, []
                row.probe, row.cost_usd, row.error = report.media.model_dump() if report.media else None, result.cost_usd, None
                session.flush()
                records.append(_record_from_row(row))
                previous_row, accepted = row, True
                break
            except BudgetExceeded:
                raise
            except Exception as exc:
                last_error = exc
                row.status, row.error = "failed", str(exc)[:4_000]
                session.flush()
        if not accepted:
            raise last_error or RuntimeError(f"segment {index} exhausted {max_attempts} generation attempts")
    return records
