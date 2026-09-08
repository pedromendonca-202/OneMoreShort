from __future__ import annotations

import pytest

from app.core.errors import HumanActionRequired
from app.metadata.schemas import VideoMetadata
from app.youtube.auth import get_credentials
from app.youtube.mock import MockYouTubeClient


def metadata() -> VideoMetadata:
    return VideoMetadata(title="Test", description="Test description", hashtags=["#Science", "#Space", "#Shorts"], tags=["test"])


def test_mock_upload_and_stats_evolve(tmp_path):
    client = MockYouTubeClient()
    uploaded = client.upload(tmp_path / "video.mp4", metadata(), "private", None)
    assert uploaded.video_id.startswith("mock-")
    assert client.video_stats([uploaded.video_id], age_minutes=60)[0].views > 0


def test_missing_oauth_secret_has_precise_human_action(tmp_path):
    with pytest.raises(HumanActionRequired) as error:
        get_credentials(tmp_path / "missing.json", tmp_path / "token.json", ["scope"])
    assert "EXACT HUMAN ACTION" in error.value.report()
