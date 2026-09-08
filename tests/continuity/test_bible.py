from __future__ import annotations

from app.continuity.bible import build_bible
from app.llm.mock import MockLLM
from app.scripting.schemas import Beat, HookType, Script
from app.storyboard.schemas import Segment, Storyboard


def test_bible_contains_every_required_continuity_section():
    script = Script(title_working="Test", beats=[Beat(index=1, start_s=0, end_s=8, purpose="hook", narration="A fact")],
                    hook_type=HookType.CURIOSITY, ending_type="statement", cta_used=False, loop_used=False, total_words=2, est_duration_s=8)
    segment = Segment(segment=1, duration=8, purpose="hook", visual_description="lab", camera="close", lens="35mm", lighting="warm",
                      characters="host", environment="lab", objects="sample", action="points", narration="A fact", dialogue=None,
                      sound_design="hum", transition_to_next="continue", continuity_state="host holds sample")
    storyboard = Storyboard(segments=[segment.model_copy(update={"segment": i}) for i in range(1, 6)], visual_style="cinematic", palette="red")
    bible = build_bible(MockLLM(), script, storyboard)
    required = {"characters", "appearance", "clothing", "hair", "accessories", "environment", "lighting", "color_palette",
                "camera", "lens", "camera_movement", "objects", "object_positions", "actions", "voice", "narrator", "accent",
                "audio_style", "visual_style", "temporal_state", "current_scene_state", "previous_scene_ending", "next_scene_starting_state"}
    assert required <= set(bible.model_fields_set)
    assert all(getattr(bible, field) for field in required)
