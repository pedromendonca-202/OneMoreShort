"""Replace paid Veo calls with an explicit, validated manual handoff."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.continuity.schemas import ContinuityBible
from app.continuity.state import planned_end_state
from app.core.models import Segment as SegmentRow
from app.core.storage import Storage
from app.editing.concat import concat_segments
from app.editing.frames import extract_first_frame, extract_last_frame
from app.editing.normalize import normalize_segment
from app.storyboard.schemas import Storyboard
from app.veo.prompt_builder import build_prompt
from app.veo.schemas import BrandStyle, SegmentRecord
from app.veo.validator import validate_segment


_NUMBERED = re.compile(r"(?:segment|clip|video)[ _-]*0*([1-5])(?:\D|$)", re.IGNORECASE)


@dataclass(frozen=True)
class ManualPromptPackage:
    inbox: Path
    prompt_files: list[Path]
    instructions: Path


@dataclass(frozen=True)
class ManualCollection:
    records: list[SegmentRecord]
    concat_path: Path


def _value(cfg: Any, section: str, field: str, default: Any) -> Any:
    return getattr(getattr(cfg, section, cfg), field, default)


def _brand(cfg: Any) -> BrandStyle:
    raw = getattr(cfg, "brand", None)
    return BrandStyle.model_validate(raw.model_dump() if hasattr(raw, "model_dump") else raw or {})


def inbox_for(production_id: str, storage: Storage, cfg: Any) -> Path:
    return storage.dir_for(production_id, "manual_input")


def export_prompts(production_id: str, storyboard: Storyboard, bible: ContinuityBible, storage: Storage, cfg: Any) -> ManualPromptPackage:
    """Write five copyable prompts plus a precise handoff instruction file."""
    folder = storage.dir_for(production_id, "prompts")
    inbox = inbox_for(production_id, storage, cfg)
    duration = float(_value(cfg, "veo", "duration_seconds", 8))
    prompts: list[Path] = []
    previous = None
    for scene in storyboard.segments:
        prompt = build_prompt(scene, bible, storyboard, previous, _brand(cfg))
        prompt = prompt.model_copy(update={"config": {**prompt.config, "duration_seconds": duration}})
        path = folder / f"manual_prompt_{scene.segment:02d}.txt"
        header = (
            f"SEGMENT {scene.segment} OF 5  |  {duration:g} seconds  |  portrait 9:16  |  no speech, no on-screen text\n"
            + (
                "HOW TO KEEP CONTINUITY IN FLOW: use 'Extend' on the previous clip, or start this clip from the last frame "
                "of the previous clip (upload it as the starting image). Do NOT restart the scene.\n"
                if scene.segment > 1
                else "This is the opening clip. Generate it first; every later clip continues from it.\n"
            )
            + "-" * 72 + "\n\n"
        )
        path.write_text(header + prompt.prompt + "\n\nNEGATIVE PROMPT:\n" + prompt.negative_prompt + "\n", encoding="utf-8")
        prompts.append(path)
        previous = planned_end_state(scene, bible)
    instructions = folder / "MANUAL_VIDEO_HANDOFF.txt"
    instructions.write_text(
        f"""ONE MORE SHORT - MANUAL VIDEO HANDOFF

WHAT YOU ARE MAKING
One continuous {duration * 5:g}-second vertical video, generated as five {duration:g} second clips.
The five clips must look like ONE uninterrupted shot: same character, wardrobe, location, light, lens, camera motion.

STEP BY STEP (Google Flow / Gemini app with your subscription credits)
1. Open manual_prompt_01.txt, paste the prompt, set portrait 9:16 and {duration:g} second length, generate.
   Pick the take whose LAST FRAME best matches the "Planned continuity state at end" in the prompt.
2. For clips 2 to 5 use ONE of these, in order of preference:
   a) Flow "Extend": extend the previous clip with the next prompt (best continuity, no restart).
   b) "Frames to video": download the previous clip, take its last frame, upload it as the START image,
      then paste the next prompt.
   c) Text only (weakest): paste the prompt; it already describes the exact end state of the previous clip.
3. Never let a clip restart the scene, cut to a new angle, add speech, subtitles, logos or on-screen text.
   Narration, captions and music are added automatically later.
4. Download each clip as MP4 (H.264/AAC where offered). 720p or 1080p are both accepted.

WHERE TO PUT THE FILES (exact folder)
   {inbox}
Names: segment_01.mp4, segment_02.mp4, segment_03.mp4, segment_04.mp4, segment_05.mp4
If names are not numbered, the system accepts exactly five video files and sorts them naturally.

WHAT HAPPENS NEXT (automatic)
Run:  python -m app.cli watch {production_id}     (waits for the five files, then continues by itself)
or:   python -m app.cli collect-clips {production_id}  then  python -m app.cli finish {production_id}
The system validates, normalizes to 1080x1920/24fps, extracts boundary frames, concatenates, narrates,
captions, mixes audio, runs the quality gate, generates title/description/hashtags and uploads (if enabled).

No Veo API request is sent in this workflow. Cost: 0 USD.
""",
        encoding="utf-8",
    )
    return ManualPromptPackage(inbox=inbox, prompt_files=prompts, instructions=instructions)


def _natural_key(path: Path) -> list[str | int]:
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", path.name)]


def _discover(inbox: Path, cfg: Any) -> list[Path]:
    extensions = {str(value).lower() for value in _value(cfg, "generation", "accepted_extensions", [".mp4", ".mov", ".mkv", ".webm"])}
    files = sorted((path for path in inbox.iterdir() if path.is_file() and path.suffix.lower() in extensions), key=_natural_key)
    numbered: dict[int, Path] = {}
    for path in files:
        match = _NUMBERED.search(path.stem)
        if match:
            number = int(match.group(1))
            if number in numbered:
                raise ValueError(f"ambiguous manual video inbox: more than one file identifies as segment {number}")
            numbered[number] = path
    if numbered:
        if set(numbered) != {1, 2, 3, 4, 5}:
            raise ValueError("manual video inbox must contain exactly numbered segments 1 through 5")
        return [numbered[index] for index in range(1, 6)]
    if bool(_value(cfg, "generation", "require_numbered_files", False)):
        raise ValueError("manual video inbox requires files named segment_01 through segment_05")
    if len(files) != 5:
        raise ValueError(f"manual video inbox needs exactly five video files; found {len(files)}")
    return files


def _row(session: Session | None, production_id: str, index: int) -> SegmentRow | None:
    return session.scalar(select(SegmentRow).where(SegmentRow.production_id == production_id, SegmentRow.index == index)) if session else None


def collect_manual_segments(production_id: str, storage: Storage, session: Session | None, cfg: Any) -> ManualCollection:
    """Validate five manually created clips and produce a normalized concat file."""
    inbox = inbox_for(production_id, storage, cfg)
    sources = _discover(inbox, cfg)
    duration = float(_value(cfg, "veo", "duration_seconds", 8))
    normalized: list[Path] = []
    records: list[SegmentRecord] = []
    for index, source in enumerate(sources, start=1):
        report = validate_segment(source, expect_seconds=duration, tolerance=max(0.25, min(1, duration * .2)))
        if not report.ok:
            raise ValueError(f"manual segment {index} ({source.name}) failed validation: {'; '.join(report.issues)}")
        output = storage.path_for(production_id, "segments", f"segment_{index:02d}_normalized.mp4")
        normalize_segment(source, output, w=int(_value(cfg, "video", "width", 1080)), h=int(_value(cfg, "video", "height", 1920)),
                          fps=int(_value(cfg, "video", "fps", 24)))
        first = storage.path_for(production_id, "frames", f"segment_{index:02d}_first.png")
        last = storage.path_for(production_id, "frames", f"segment_{index:02d}_last.png")
        extract_first_frame(output, first)
        extract_last_frame(output, last)
        row = _row(session, production_id, index)
        if session and row is None:
            row = SegmentRow(production_id=production_id, index=index)
            session.add(row)
        if row is not None:
            row.status, row.file_path, row.normalized_path = "validated", str(source), str(output)
            row.first_frame_path, row.last_frame_path = str(first), str(last)
            row.probe, row.cost_usd, row.error = report.media.model_dump() if report.media else None, 0, None
        normalized.append(output)
        records.append(SegmentRecord(index=index, status="validated", path=output, first_frame_path=first, last_frame_path=last, cost_usd=0))
    concat_path = storage.path_for(production_id, "renders", "segments_concat.mp4")
    concat_segments(normalized, concat_path)
    if session:
        session.flush()
    return ManualCollection(records=records, concat_path=concat_path)
