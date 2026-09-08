"""The mixed track and the final render must be 48 kHz AAC/PCM, never loudnorm's internal 192 kHz."""
from __future__ import annotations

from app.audio.mixer import mix_audio
from app.audio.narration import narrate
from app.audio.tts.mock import MockTTS
from app.captions.aligner import align_words, build_phrases
from app.captions.ass_renderer import render_ass
from app.captions.style import CaptionStyle
from app.core.storage import Storage
from app.editing.probe import probe
from app.editing.render import render_final
from app.editing.synth import synth_segment
from app.llm.mock import MockLLM
from app.scripting.schemas import Beat, HookType, Script


def _script() -> Script:
    return Script(
        title_working="Sample rate check", hook_type=HookType.CURIOSITY, ending_type="statement",
        cta_used=False, loop_used=False, total_words=8, est_duration_s=3,
        beats=[Beat(index=1, start_s=0, end_s=1.5, purpose="hook", narration="One two three four"),
               Beat(index=2, start_s=1.5, end_s=3, purpose="payoff", narration="five six seven eight")],
    )


def test_mix_and_render_output_48khz(tmp_path, settings):
    storage = Storage(tmp_path / "storage")
    video = synth_segment(tmp_path / "video.mp4", seconds=3.0, color="black", label="v", with_audio=True)
    narration = narrate(_script(), MockTTS(), MockLLM(), storage, "OMS-TEST", 5)

    mixed = mix_audio(video, narration, None, tmp_path / "mixed.wav", settings)
    assert probe(mixed).sample_rate == 48000

    ass = render_ass(build_phrases(align_words(narration), 3), CaptionStyle(), tmp_path / "captions.ass")
    final = render_final(video, mixed, ass, None, tmp_path / "final.mp4", 5, tmp_path)
    info = probe(final)
    assert info.sample_rate == 48000
    assert info.acodec == "aac" and info.vcodec == "h264"
