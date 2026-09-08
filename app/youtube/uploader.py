"""Resumable YouTube upload implementation."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from app.metadata.schemas import VideoMetadata
from app.youtube.schemas import UploadResult


class GoogleYouTubeClient:
    def __init__(self, credentials):
        from googleapiclient.discovery import build
        self.service = build("youtube", "v3", credentials=credentials, cache_discovery=False)

    def upload(self, video: Path | str, metadata: VideoMetadata, privacy: str, publish_at: datetime | None) -> UploadResult:
        from googleapiclient.http import MediaFileUpload

        status = {"privacyStatus": privacy, "selfDeclaredMadeForKids": False}
        if publish_at:
            status["privacyStatus"] = "private"
            status["publishAt"] = publish_at.isoformat()
        body = {
            "snippet": {"title": metadata.title, "description": metadata.description, "tags": metadata.tags,
                        "categoryId": metadata.category_id, "defaultLanguage": "en"},
            "status": status,
        }
        request = self.service.videos().insert(part="snippet,status", body=body,
            media_body=MediaFileUpload(str(video), mimetype="video/mp4", resumable=True, chunksize=8 * 1024 * 1024))
        response = None
        while response is None:
            _, response = request.next_chunk()
        video_id = response["id"]
        return UploadResult(video_id=video_id, status=response.get("status", {}).get("uploadStatus", "uploaded"),
                            url=f"https://www.youtube.com/watch?v={video_id}")

    def video_stats(self, ids: list[str], age_minutes: int = 0):
        from app.youtube.data_api import YouTubeDataAPI

        return YouTubeDataAPI(service=self.service).video_stats(ids, age_minutes)

    def post_comment(self, video_id: str, text: str) -> str | None:
        """Top-level comment used as the pinned comment (pinning itself is a manual Studio action)."""
        body = {"snippet": {"videoId": video_id, "topLevelComment": {"snippet": {"textOriginal": text}}}}
        response = self.service.commentThreads().insert(part="snippet", body=body).execute()
        return response.get("id")
