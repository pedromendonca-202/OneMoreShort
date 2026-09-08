from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.scripting.schemas import Beat, HookType, Script


def beat(index: int, start: float, end: float) -> Beat:
    return Beat(index=index, start_s=start, end_s=end, purpose="hook", narration=f"Line {index}")


def script(beats: list[Beat]) -> Script:
    return Script(title_working="Test", beats=beats, hook_type=HookType.CURIOSITY, ending_type="statement", cta_used=False,
                  loop_used=False, total_words=5, est_duration_s=5)


def test_script_rejects_overlapping_beats():
    with pytest.raises(ValidationError, match="overlap"):
        script([beat(1, 0, 5), beat(2, 4, 8)])


def test_script_rejects_duration_over_maximum():
    with pytest.raises(ValidationError, match="maximum"):
        script([beat(1, 0, 40.1)])


def test_estimate_duration_accepts_text_and_word_count():
    from app.scripting.generator import estimate_duration

    assert estimate_duration("one two three", 180) == 1.0
    assert estimate_duration(90, 180) == 30.0
