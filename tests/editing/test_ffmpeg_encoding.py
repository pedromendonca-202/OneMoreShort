"""ffmpeg diagnostics must survive non-cp1252 bytes (accented OneDrive paths) on Windows."""
from __future__ import annotations

import pytest

from app.core.errors import FFmpegError
from app.editing.ffmpeg import run_ffmpeg, run_ffprobe
from app.editing.probe import probe
from app.editing.synth import synth_segment


@pytest.fixture
def accented_dir(tmp_path):
    folder = tmp_path / "Área de Trabalho Ção"
    folder.mkdir()
    return folder


def test_ffmpeg_error_stderr_is_decoded_text_with_accented_path(accented_dir):
    missing = accented_dir / "não existe.mp4"

    with pytest.raises(FFmpegError) as excinfo:
        run_ffmpeg(["-i", str(missing), "-f", "null", "-"], cwd=accented_dir)

    err = excinfo.value
    assert isinstance(err.stderr, str)
    assert "não existe.mp4" in err.stderr


def test_ffprobe_on_accented_path_returns_clean_result(accented_dir):
    clip = synth_segment(accented_dir / "clipe ção.mp4", seconds=0.5, color="red", label="x", with_audio=True)

    completed = run_ffprobe(["-v", "error", "-show_entries", "format=duration", "-of", "json", str(clip)], cwd=accented_dir)

    assert completed.returncode == 0
    assert isinstance(completed.stdout, str) and "duration" in completed.stdout
    assert probe(clip).has_audio
