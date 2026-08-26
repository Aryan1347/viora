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

    video_id = "5MgBikgcWnY"
    instances = [
        "https://pipedapi.kavin.rocks",
        "https://piped-api.garudalinux.org",
        "https://api.piped.projectsegfau.lt",
        "https://pipedapi.adminforge.de",
    ]

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            for base in instances:
                try:
                    r = await client.get(f"{base}/streams/{video_id}")
                    if r.status_code == 200 and r.text.startswith("{"):
                        data = r.json()
                        if "videoStreams" in data:
                            best = data["videoStreams"][0]
                            return {
                                "status": "ok",
                                "instance": base,
                                "title": data.get("title"),
                                "duration": data.get("duration"),
                                "quality": best.get("quality"),
                                "stream_url": best["url"][:80] + "...",
                            }
                        return {"status": "bad_response", "instance": base, "data": str(data)[:200]}
                except Exception as e:
                    continue

        return {"status": "error", "error": "all instances failed"}

    except Exception as e:
        return {"status": "error", "error": str(e)}