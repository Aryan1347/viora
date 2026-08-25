from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# ── Request ─────────────────────────────────────────────────────
class AnalyzeRequest(BaseModel):
    url: str


# ── YouTube metadata ────────────────────────────────────────────
class VideoMetadata(BaseModel):
    video_id: str
    title: str
    description: str
    tags: list[str]
    duration: int
    view_count: int
    like_count: int
    comment_count: int
    published_at: datetime
    thumbnail_url: str
    channel_id: str
    channel_title: str
    subscriber_count: int
    total_video_count: int


class CommentItem(BaseModel):
    text: str
    like_count: int
    published_at: datetime


class YouTubeData(BaseModel):
    metadata: VideoMetadata
    comments: list[CommentItem]


# ── Health ───────────────────────────────────────────────────────
class HealthResponse(BaseModel):
    status: str
    env: str
    supabase: str
    qdrant: str