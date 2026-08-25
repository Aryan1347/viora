import modal
import os

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg")
    .pip_install(
        "yt-dlp>=2024.1.0",
        "bgutil-ytdlp-pot-provider",
    )
)

app = modal.App("viora-pipeline", image=image)


@app.function(timeout=120, memory=512, image=image)
def download_short(url: str) -> dict:
    import yt_dlp

    out_dir = "/tmp/viora_downloads"
    os.makedirs(out_dir, exist_ok=True)

    ydl_opts = {
        "format": "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": f"{out_dir}/%(id)s.%(ext)s",
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        video_id = info["id"]
        ext = info.get("ext", "mp4")

    filepath = f"{out_dir}/{video_id}.{ext}"

    if not os.path.exists(filepath):
        candidates = os.listdir(out_dir)
        match = [f for f in candidates if f.startswith(video_id)]
        if not match:
            raise FileNotFoundError(f"No file for {video_id}")
        filepath = f"{out_dir}/{match[0]}"

    size_bytes = os.path.getsize(filepath)
    return {
        "path": filepath,
        "filename": os.path.basename(filepath),
        "size_bytes": size_bytes,
        "size_mb": round(size_bytes / (1024 * 1024), 2),
        "video_id": video_id,
        "title": info.get("title", ""),
        "duration_sec": info.get("duration", 0),
    }


@app.local_entrypoint()
def main():
    test_url = "https://www.youtube.com/shorts/5MgBikgcWnY"
    print(f"[TEST] Sending to Modal: {test_url}")
    result = download_short.remote(test_url)
    print("[TEST] Result:")
    for k, v in result.items():
        print(f"  {k}: {v}")