from __future__ import annotations

from app.continuity.schemas import ContinuityBible
from app.core.models import Production
from app.core.states import State
from app.editing.synth import synth_segment
from app.manual_video.workflow import collect_manual_segments, export_prompts, inbox_for
from app.storyboard.schemas import Segment, Storyboard


def _storyboard() -> Storyboard:
    return Storyboard(segments=[
        Segment(segment=i, duration=1, purpose="scene", visual_description="A lab scene", camera="close-up", lens="35mm", lighting="warm",
                characters="host", environment="lab", objects="sample", action="moves", narration=f"Line {i}", dialogue=None,
                sound_design="hum", transition_to_next="continue", continuity_state="same scene")
        for i in range(1, 6)
    ], visual_style="cinematic", palette="red")


def _bible() -> ContinuityBible:
    return ContinuityBible(**{field: "stable detail" for field in ContinuityBible.model_fields})


def test_export_prompts_and_collect_five_manually_created_segments(session, storage, settings):
    settings.veo.duration_seconds = 1
    production_id = "OMS-20260907-0099"
    session.add(Production(id=production_id, state=State.GENERATING))
    session.flush()
    package = export_prompts(production_id, _storyboard(), _bible(), storage, settings)
    assert len(package.prompt_files) == 5 and package.instructions.exists()
    inbox = inbox_for(production_id, storage, settings)
    for i in range(1, 6):
        synth_segment(inbox / f"segment_{i}.mp4", 1, "black", f"manual {i}", with_audio=True)
    result = collect_manual_segments(production_id, storage, session, settings)
    assert len(result.records) == 5
    assert result.concat_path.exists()
    assert [record.index for record in result.records] == [1, 2, 3, 4, 5]


def test_manual_collector_refuses_ambiguous_or_incomplete_inbox(storage, settings):
    inbox_for("OMS-20260907-0100", storage, settings).joinpath("one.mp4").touch()
    try:
        collect_manual_segments("OMS-20260907-0100", storage, None, settings)
    except ValueError as error:
        assert "five" in str(error).lower()
    else:
        raise AssertionError("expected manual input validation to fail")
