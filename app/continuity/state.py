"""Convert planned or observed boundaries into a reusable end-state contract."""
from __future__ import annotations

from app.continuity.schemas import ContinuityBible, SegmentEndState
from app.storyboard.schemas import Segment


def planned_end_state(segment: Segment, bible: ContinuityBible) -> SegmentEndState:
    """Fallback used before a vision observer can describe the actual last frame."""
    return SegmentEndState(
        description=segment.continuity_state,
        character_positions=bible.current_scene_state,
        camera=bible.camera,
        lighting=bible.lighting,
        objects=bible.object_positions,
        motion=bible.camera_movement,
    )
