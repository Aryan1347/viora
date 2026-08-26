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
    import httpx
    import tempfile
    import os

    video_id = "5MgBikgcWnY"

    try:
        # Step 1 -- get stream URL from Piped
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(f"https://api.piped.yt/streams/{video_id}")
            data = r.json()

        if "videoStreams" not in data:
            return {"status": "error", "error": str(data)}

        # Step 2 -- pick best video stream
        streams = data["videoStreams"]
        best = sorted(streams, key=lambda x: x.get("quality", "0"), reverse=True)[0]
        stream_url = best["url"]

        return {
            "status": "ok",
            "title": data.get("title"),
            "duration": data.get("duration"),
            "stream_url": stream_url[:80] + "...",  # truncate for display
            "quality": best.get("quality"),
            "mime": best.get("mimeType"),
        }

    except Exception as e:
        import traceback
        return {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }