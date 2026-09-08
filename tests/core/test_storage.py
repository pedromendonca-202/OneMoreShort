import pytest

from app.core.storage import Storage


def test_paths_are_created(tmp_path):
    st = Storage(tmp_path / "storage")
    p = st.path_for("OMS-20260907-0001", "segments", "segment_01.mp4")
    assert p.parent.exists()
    assert p.name == "segment_01.mp4"
    assert "OMS-20260907-0001" in p.parts


def test_unknown_kind_rejected(tmp_path):
    with pytest.raises(ValueError):
        Storage(tmp_path).path_for("OMS-20260907-0001", "nope", "x")


def test_relpath_is_relative_and_posix(tmp_path):
    st = Storage(tmp_path / "storage")
    p = st.path_for("OMS-20260907-0001", "captions", "captions.ass")
    rel = st.relpath(p, cwd=p.parent)
    assert rel == "captions.ass"
