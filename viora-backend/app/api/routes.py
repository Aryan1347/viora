from fastapi import APIRouter, HTTPException
from app.models.schemas import AnalyzeRequest, YouTubeData, HealthResponse
from app.services.youtube import fetch_youtube_data
from app.core.config import get_settings
from app.core.supabase import get_supabase
from app.core.qdrant import get_qdrant

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health():
    s = get_settings()

    # Ping Supabase
    try:
        get_supabase().table("channels").select("channel_id").limit(1).execute()
        sb_status = "ok"
    except Exception as e:
        sb_status = f"error: {e}"

    # Ping Qdrant
    try:
        get_qdrant().get_collections()
        qdrant_status = "ok"
    except Exception as e:
        qdrant_status = f"error: {e}"

    return HealthResponse(
        status="ok",
        env=s.app_env,
        supabase=sb_status,
        qdrant=qdrant_status,
    )


@router.post("/analyze/youtube", response_model=YouTubeData)
async def analyze_youtube(body: AnalyzeRequest):
    """
    Step 2 — YouTube Data API integration.
    Returns raw metadata + comments for a given Shorts URL.
    Modal processing (Steps 3–10) wired in next session.
    """
    try:
        data = await fetch_youtube_data(body.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"YouTube API error: {e}")

    return data


@router.get("/test-download")
async def test_download():
    import yt_dlp
    import tempfile
    import os

    url = "https://www.youtube.com/shorts/5MgBikgcWnY"
    out_dir = tempfile.mkdtemp()

    ydl_opts = {
        "format": "best[ext=mp4]/best",
        "outtmpl": f"{out_dir}/%(id)s.%(ext)s",
        "quiet": True,
        "noplaylist": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    files = os.listdir(out_dir)
    size = os.path.getsize(f"{out_dir}/{files[0]}") if files else 0

    return {
        "status": "ok",
        "title": info.get("title"),
        "duration": info.get("duration"),
        "size_mb": round(size / (1024*1024), 2),
        "file": files[0] if files else None,
    }