from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.metadata.schemas import VideoMetadata


def valid_metadata(**changes):
    values = dict(title="Why Mars Is Still Hiding Water", description="A concise source-aware explanation.",
                  hashtags=["#Science", "#Space", "#Shorts"], tags=["mars", "science"], category_id="28", thumbnail_time_s=2)
    values.update(changes)
    return VideoMetadata(**values)


def test_metadata_enforces_youtube_limits_and_shorts_tag():
    assert "#Shorts" in valid_metadata().hashtags
    with pytest.raises(ValidationError):
        valid_metadata(title="x" * 101)
    with pytest.raises(ValidationError, match="Shorts"):
        valid_metadata(hashtags=["#Science", "#Space", "#Mars"])
    with pytest.raises(ValidationError):
        valid_metadata(tags=["x" * 501])
