from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import httpx
import pytest

from app.trends.gtrends_rss_source import GoogleTrendsRSSSource
from app.trends.hackernews_source import HackerNewsSource
from app.trends.news_rss_source import GoogleNewsRSSSource
from app.trends.reddit_source import RedditSource
from app.trends.wikipedia_source import WikipediaTopViewedSource
from app.trends.youtube_source import YouTubeTrendSource


FIXTURES = Path(__file__).parents[1] / "fixtures" / "trends"


def client_for(routes: dict[str, str | dict | list]) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        for marker, body in routes.items():
            if marker in str(request.url):
                if isinstance(body, (dict, list)):
                    return httpx.Response(200, json=body, request=request)
                return httpx.Response(200, text=body, request=request)
        return httpx.Response(404, request=request)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_youtube_parser_normalizes_metrics_and_metadata():
    source = YouTubeTrendSource(
        api_key="not-a-real-key",
        categories=["28"],
        client=client_for({"youtube/v3/videos": json.loads((FIXTURES / "youtube.json").read_text())}),
    )
    signals = source.fetch(limit=3)
    assert len(signals) == 1
    assert signals[0].source == "youtube"
    assert signals[0].metrics == {"views": 1_200_000.0, "likes": 56_000.0, "comments": 2_200.0}
    assert signals[0].url == "https://www.youtube.com/watch?v=abc123"


def test_reddit_parser_skips_stickied_posts():
    source = RedditSource(
        subreddits=["science"],
        client=client_for({"/r/science/hot.json": json.loads((FIXTURES / "reddit.json").read_text())}),
    )
    signals = source.fetch(limit=5)
    assert len(signals) == 1
    assert signals[0].metrics["score"] == 42_000
    assert signals[0].url == "https://www.reddit.com/r/science/comments/abc/mars/"


def test_news_and_google_trends_parse_rss_fixtures():
    news = GoogleNewsRSSSource(client=client_for({"news.google.com": (FIXTURES / "news.xml").read_text()})).fetch(limit=5)
    trends = GoogleTrendsRSSSource(client=client_for({"trends.google.com": (FIXTURES / "gtrends.xml").read_text()})).fetch(limit=5)
    assert news[0].category == "Science" and news[0].published_at is not None
    assert trends[0].metrics["traffic"] == 200_000
    assert trends[0].url == "https://example.test/mars-trends"


def test_hacker_news_and_wikipedia_parse_api_payloads():
    hn = HackerNewsSource(client=client_for({
        "topstories.json": [101, 102],
        "/item/101.json": {"id": 101, "title": "A cool space discovery", "url": "https://example.test/space", "score": 900, "descendants": 85, "time": 1788782400, "type": "story"},
        "/item/102.json": {"id": 102, "title": "Ask HN", "score": 9, "type": "comment"},
    })).fetch(limit=3)
    wiki = WikipediaTopViewedSource(today=lambda: date(2026, 9, 7), client=client_for({
        "pageviews/top": {"items": [{"articles": [
            {"article": "Mars", "views": 345678, "rank": 1},
            {"article": "Main_Page", "views": 999999, "rank": 0},
        ]}]}
    })).fetch(limit=3)
    assert len(hn) == 1 and hn[0].metrics["comments"] == 85
    assert len(wiki) == 1 and wiki[0].title == "Mars"
    assert wiki[0].url == "https://en.wikipedia.org/wiki/Mars"


@pytest.mark.parametrize("factory", [
    lambda: RedditSource(subreddits=["science"], client=client_for({"reddit.com": "not json"})),
    lambda: GoogleNewsRSSSource(client=client_for({"news.google.com": "<not valid"})),
])
def test_malformed_source_response_returns_no_signals(factory):
    assert factory().fetch(limit=5) == []
