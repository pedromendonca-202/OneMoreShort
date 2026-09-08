from __future__ import annotations

import pytest

from app.continuity.schemas import ContinuityBible
from app.storyboard.schemas import Segment, Storyboard
from app.veo.schemas import BrandStyle


@pytest.fixture
def bible() -> ContinuityBible:
    return ContinuityBible(
        characters="One adult presenter", appearance="short dark hair, brown eyes", clothing="black jacket", hair="short dark hair",
        accessories="silver watch", environment="modern science lab", lighting="warm key light from camera left", color_palette="black, red, white",
        camera="eye-level medium close-up", lens="35mm", camera_movement="slow forward dolly", objects="a clear sample vial",
        object_positions="vial in right hand at chest height", actions="presenter turns toward the vial", voice="none in Veo",
        narrator="one post-production narrator", accent="General American", audio_style="ambient lab only", visual_style="cinematic",
        temporal_state="same afternoon", current_scene_state="presenter holds vial", previous_scene_ending="scene begins",
        next_scene_starting_state="continue holding the vial",
    )


@pytest.fixture
def storyboard() -> Storyboard:
    segments = [
        Segment(segment=i, duration=1, purpose="scene", visual_description="Presenter in the lab", camera="medium close-up", lens="35mm",
                lighting="warm", characters="presenter", environment="lab", objects="vial", action="turns", narration=f"Line {i}",
                dialogue=None, sound_design="lab hum", transition_to_next="continue motion", continuity_state="same vial position")
        for i in range(1, 6)
    ]
    return Storyboard(segments=segments, visual_style="cinematic", palette="black and red")


@pytest.fixture
def brand() -> BrandStyle:
    return BrandStyle(name="OneMoreShort", visual_style="bold cinematic", palette="black red white", narrator_persona="curious American narrator")
