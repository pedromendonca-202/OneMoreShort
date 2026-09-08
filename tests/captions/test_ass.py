from __future__ import annotations

from app.audio.schemas import BeatAudio, NarrationPlan, WordTiming
from app.captions.aligner import align_words, build_phrases
from app.captions.ass_renderer import render_ass
from app.captions.style import CaptionStyle
from app.scripting.schemas import Beat


def test_ass_phrases_are_monotonic_and_render(tmp_path):
    beat = Beat(index=1, start_s=1, end_s=3, purpose="hook", narration="hello brave new world")
    narration = NarrationPlan(beats=[BeatAudio(beat=beat, path=tmp_path / "a.wav", start_s=1, duration_s=2,
                                               words=[WordTiming(word="hello", start_s=0, end_s=.4), WordTiming(word="brave", start_s=.4, end_s=.8),
                                                      WordTiming(word="new", start_s=.8, end_s=1.2), WordTiming(word="world", start_s=1.2, end_s=1.6)])],
                              total_s=3)
    phrases = build_phrases(align_words(narration), max_words=2)
    assert all(right.start_s >= left.end_s for left, right in zip(phrases, phrases[1:]))
    ass = render_ass(phrases, CaptionStyle(), tmp_path / "captions.ass")
    assert ass.exists() and "Dialogue:" in ass.read_text(encoding="utf-8-sig")
