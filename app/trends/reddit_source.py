"""Reddit's public JSON listing endpoint."""
from __future__ import annotations

from datetime import UTC, datetime

from app.trends.base import HTTPTrendSource, TrendSignal, as_float, bounded_limit


class RedditSource(HTTPTrendSource):
    name = "reddit"

    def __init__(self, subreddits: list[str], *, timeout_s: float = 20, client=None):
        super().__init__(timeout_s=timeout_s, client=client)
        self.subreddits = subreddits

    def fetch(self, limit: int) -> list[TrendSignal]:
        try:
            per_subreddit = max(1, bounded_limit(limit) // max(1, len(self.subreddits)))
            out: list[TrendSignal] = []
            for subreddit in self.subreddits:
                url = f"https://www.reddit.com/r/{subreddit}/hot.json"
                data = self._get(url, params={"limit": per_subreddit, "raw_json": 1}, headers={"User-Agent": "OneMoreShort/0.1 trend research"}).json()
                for child in (data.get("data") or {}).get("children") or []:
                    post = child.get("data") or {}
                    if post.get("stickied") or not post.get("title"):
                        continue
                    permalink = post.get("permalink")
                    out.append(TrendSignal(
                        source=self.name,
                        title=str(post["title"]),
                        url=f"https://www.reddit.com{permalink}" if permalink else None,
                        summary=str(post.get("selftext") or "")[:2_000] or None,
                        category=subreddit,
                        metrics={
                            "score": as_float(post.get("score")),
                            "comments": as_float(post.get("num_comments")),
                            "upvote_ratio": as_float(post.get("upvote_ratio")),
                        },
                        published_at=datetime.fromtimestamp(as_float(post.get("created_utc")), tz=UTC) if post.get("created_utc") else None,
                    ))
                    if len(out) >= limit:
                        return out
            return out
        except Exception as exc:
            return self._failure(exc, limit=limit)
