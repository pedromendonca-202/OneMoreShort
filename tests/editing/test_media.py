from __future__ import annotations

import pytest

from app.editing.concat import concat_segments
from app.editing.frames import extract_last_frame
from app.editing.normalize import normalize_segment
from app.editing.probe import probe
from app.editing.synth import synth_segment


@pytest.fixture
def clip(tmp_path):
    return synth_segment(tmp_path / "source.mp4", seconds=1.0, color="red", label="source", with_audio=True)


def test_synth_and_probe_report_portrait_h264_aac(clip):
    info = probe(clip)
    assert 0.8 <= info.duration_s <= 1.2
    assert (info.width, info.height, round(info.fps)) == (1080, 1920, 24)
    assert info.vcodec == "h264" and info.acodec == "aac" and info.has_audio


def test_extract_last_frame_writes_png(clip, tmp_path):
    frame = extract_last_frame(clip, tmp_path / "last.png")
    assert frame.exists() and frame.stat().st_size > 0


def test_normalize_produces_standard_portrait_fps(clip, tmp_path):
    normalized = normalize_segment(clip, tmp_path / "normalized.mp4")
    info = probe(normalized)
    assert (info.width, info.height, round(info.fps)) == (1080, 1920, 24)


def test_concat_duration_is_approximately_sum(clip, tmp_path):
    second = synth_segment(tmp_path / "second.mp4", seconds=1.0, color="blue", label="second", with_audio=True)
    joined = concat_segments([clip, second], tmp_path / "joined.mp4")
    info = probe(joined)
    assert 1.7 <= info.duration_s <= 2.3
    assert info.has_audio
