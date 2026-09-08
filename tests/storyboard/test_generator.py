from __future__ import annotations

from app.llm.mock import MockLLM
from app.scripting.schemas import Beat, HookType, Script
from app.storyboard.generator import generate_storyboard
from app.storyboard.schemas import Segment, Storyboard


def script() -> Script:
    beats = [Beat(index=i + 1, start_s=i * 8, end_s=(i + 1) * 8, purpose="hook" if i == 0 else "payoff", narration=f"Narration {i + 1}") for i in range(5)]
    return Script(title_working="Mars", beats=beats, hook_type=HookType.CURIOSITY, ending_type="statement", cta_used=False,
                  loop_used=False, total_words=20, est_duration_s=40)


def segment(i: int) -> Segment:
    return Segment(segment=i, duration=8, purpose="scene", visual_description="visual", camera="close", lens="35mm", lighting="day",
                   characters="host", environment="lab", objects="sample", action="moves", narration="wrong", dialogue=None,
                   sound_design="ambient", transition_to_next="continue", continuity_state="same scene")


def test_generator_maps_beats_into_their_five_time_windows(settings):
    raw = Storyboard(segments=[segment(i) for i in range(1, 6)], visual_style="cinematic", palette="red")
    llm = MockLLM(handlers={"Storyboard": lambda req: raw})
    out = generate_storyboard(llm, script(), settings)
    assert len(out.segments) == 5
    assert [part.narration for part in out.segments] == [f"Narration {i}" for i in range(1, 6)]
    assert [part.duration for part in out.segments] == [8] * 5


def test_plain_mock_llm_can_build_a_normalized_five_segment_storyboard(settings):
    out = generate_storyboard(MockLLM(), script(), settings)
    assert [part.segment for part in out.segments] == [1, 2, 3, 4, 5]
