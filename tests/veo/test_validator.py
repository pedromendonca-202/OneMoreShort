from __future__ import annotations

from app.editing.synth import synth_segment
from app.editing.ffmpeg import run_ffmpeg
from app.veo.validator import validate_segment


def test_validator_accepts_expected_clip_and_flags_short_clip(tmp_path):
    valid = synth_segment(tmp_path / "valid.mp4", 1, "black", "valid", with_audio=True)
    short = synth_segment(tmp_path / "short.mp4", 0.2, "black", "short", with_audio=True)
    assert validate_segment(valid, expect_seconds=1, tolerance=0.3).ok
    report = validate_segment(short, expect_seconds=1, tolerance=0.3)
    assert not report.ok and any("duration" in issue for issue in report.issues)


def test_validator_flags_landscape_and_silent_clips(tmp_path):
    silent = synth_segment(tmp_path / "silent.mp4", 1, "black", "silent", with_audio=False)
    landscape = tmp_path / "landscape.mp4"
    run_ffmpeg(["-y", "-f", "lavfi", "-i", "color=c=black:s=1920x1080:r=24:d=1", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(landscape)], cwd=tmp_path)
    assert any("audio" in issue for issue in validate_segment(silent, expect_seconds=1).issues)
    assert any("portrait" in issue for issue in validate_segment(landscape, expect_seconds=1).issues)
