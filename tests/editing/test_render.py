from __future__ import annotations

from app.audio.mixer import mix_audio
from app.audio.narration import narrate
from app.audio.tts.mock import MockTTS
from app.captions.aligner import align_words, build_phrases
from app.captions.ass_renderer import render_ass
from app.captions.style import CaptionStyle
from app.editing.probe import probe
from app.editing.render import render_final
from app.editing.synth import synth_segment
from app.llm.mock import MockLLM
from app.scripting.schemas import Beat, HookType, Script


def test_final_render_is_vertical_has_audio_and_is_bounded(tmp_path, storage, settings):
    video = synth_segment(tmp_path / "video.mp4", 1, "black", "source", with_audio=True)
    script = Script(title_working="Test", beats=[Beat(index=1, start_s=0, end_s=1, purpose="hook", narration="Hello world")],
                    hook_type=HookType.CURIOSITY, ending_type="statement", cta_used=False, loop_used=False, total_words=2, est_duration_s=1)
    narration = narrate(script, MockTTS(wpm=120), MockLLM(), storage, "OMS-20260907-0003", max_total_s=2)
    mixed = mix_audio(video, narration, None, tmp_path / "mixed.wav", settings)
    ass = render_ass(build_phrases(align_words(narration)), CaptionStyle(), tmp_path / "captions.ass")
    final = render_final(video, mixed, ass, None, tmp_path / "final.mp4", max_duration_s=2, cwd=tmp_path)
    info = probe(final)
    assert (info.width, info.height) == (1080, 1920)
    assert info.has_audio and info.duration_s <= 2.1 and info.size_bytes > 0
