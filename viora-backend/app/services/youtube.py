import re
import httpx
from app.core.config import get_settings
from app.models.schemas import VideoMetadata, CommentItem, YouTubeData
from datetime import datetime

BASE = "https://www.googleapis.com/youtube/v3"


def extract_video_id(url: str) -> str:
    """
    Handles all YouTube Shorts URL formats:
      https://youtube.com/shorts/VIDEO_ID
      https://youtu.be/VIDEO_ID
      https://www.youtube.com/watch?v=VIDEO_ID
    """
    patterns = [
        r"youtube\.com/shorts/([a-zA-Z0-9_-]{11})",
        r"youtu\.be/([a-zA-Z0-9_-]{11})",
        r"[?&]v=([a-zA-Z0-9_-]{11})",
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    raise ValueError(f"Could not extract video_id from URL: {url}")


async def fetch_youtube_data(url: str) -> YouTubeData:
    api_key = get_settings().youtube_api_key
    video_id = extract_video_id(url)

    async with httpx.AsyncClient(timeout=10) as client:
        # ── videos.list ─────────────────────────────────────────
        v_resp = await client.get(f"{BASE}/videos", params={
            "part": "snippet,statistics,contentDetails",
            "id": video_id,
            "key": api_key,
        })
        v_resp.raise_for_status()
        v_data = v_resp.json()

        if not v_data.get("items"):
            raise ValueError(f"Video not found or private: {video_id}")

        item = v_data["items"][0]
        snippet = item["snippet"]
        stats = item["statistics"]
        channel_id = snippet["channelId"]

        # Parse ISO 8601 duration → seconds
        raw_duration = item["contentDetails"]["duration"]  # e.g. PT1M30S
        duration_s = _parse_duration(raw_duration)

        # ── channels.list ────────────────────────────────────────
        c_resp = await client.get(f"{BASE}/channels", params={
            "part": "statistics",
            "id": channel_id,
            "key": api_key,
        })
        c_resp.raise_for_status()
        c_data = c_resp.json()
        c_stats = c_data["items"][0]["statistics"] if c_data.get("items") else {}

        # ── commentThreads.list ──────────────────────────────────
        comments: list[CommentItem] = []
        try:
            cm_resp = await client.get(f"{BASE}/commentThreads", params={
                "part": "snippet",
                "videoId": video_id,
                "maxResults": 20,
                "order": "relevance",
                "key": api_key,
            })
            cm_resp.raise_for_status()
            for c in cm_resp.json().get("items", []):
                top = c["snippet"]["topLevelComment"]["snippet"]
                comments.append(CommentItem(
                    text=top["textDisplay"],
                    like_count=int(top.get("likeCount", 0)),
                    published_at=datetime.fromisoformat(
                        top["publishedAt"].replace("Z", "+00:00")
                    ),
                ))
        except Exception:
            pass  # Comments disabled on some videos — not fatal

    metadata = VideoMetadata(
        video_id=video_id,
        title=snippet.get("title", ""),
        description=snippet.get("description", ""),
        tags=snippet.get("tags", []),
        duration=duration_s,
        view_count=int(stats.get("viewCount", 0)),
        like_count=int(stats.get("likeCount", 0)),
        comment_count=int(stats.get("commentCount", 0)),
        published_at=datetime.fromisoformat(
            snippet["publishedAt"].replace("Z", "+00:00")
        ),
        thumbnail_url=snippet["thumbnails"].get("maxres", {}).get("url")
            or snippet["thumbnails"].get("high", {}).get("url", ""),
        channel_id=channel_id,
        channel_title=snippet.get("channelTitle", ""),
        subscriber_count=int(c_stats.get("subscriberCount", 0)),
        total_video_count=int(c_stats.get("videoCount", 0)),
    )

    return YouTubeData(metadata=metadata, comments=comments)


def _parse_duration(iso: str) -> int:
    """PT1H2M3S → seconds"""
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso)
    if not m:
        return 0
    h, mn, s = (int(x or 0) for x in m.groups())
    return h * 3600 + mn * 60 + s