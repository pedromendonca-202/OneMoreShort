from __future__ import annotations

from app.audio.narration import narrate
from app.audio.tts.mock import MockTTS
from app.llm.mock import MockLLM
from app.scripting.schemas import Beat, HookType, Script


def script(text="One two three four") -> Script:
    return Script(title_working="Test", beats=[Beat(index=1, start_s=0, end_s=4, purpose="hook", narration=text)],
                  hook_type=HookType.CURIOSITY, ending_type="statement", cta_used=False, loop_used=False,
                  total_words=len(text.split()), est_duration_s=4)


def test_mock_tts_narration_returns_timed_audio(storage):
    plan = narrate(script(), MockTTS(wpm=120), MockLLM(), storage, "OMS-20260907-0001", max_total_s=10)
    assert len(plan.beats) == 1 and plan.total_s > 0
    assert plan.beats[0].path.exists() and len(plan.beats[0].words or []) == 4


def test_overlength_narration_uses_llm_tightening(storage):
    llm = MockLLM(handlers={"TightenedText": lambda req: {"text": "short line"}})
    plan = narrate(script("one two three four five six seven eight nine ten"), MockTTS(wpm=60), llm, storage,
                   "OMS-20260907-0002", max_total_s=3)
    assert plan.total_s <= 3
    assert any(call.task == "tighten_narration" for call in llm.calls)
