from fastapi import FastAPI, Request
import asyncio
import os
import random
from moviepy.editor import VideoFileClip
import yt_dlp
import dropbox  # 👈 NEW

app = FastAPI()

# Serve local files (optional, not needed if using Dropbox)
from fastapi.staticfiles import StaticFiles
app.mount("/downloads", StaticFiles(directory="downloads"), name="downloads")

# 🔑 Dropbox token (set this in Render environment variables)
DROPBOX_ACCESS_TOKEN = os.getenv("DROPBOX_TOKEN")

def upload_to_dropbox(local_path: str, dropbox_path: str):
    """Uploads a file to Dropbox and returns a direct download link"""
    if not DROPBOX_ACCESS_TOKEN:
        print("⚠️ Dropbox token missing — skipping upload.")
        return None

    try:
        dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)

        with open(local_path, "rb") as f:
            dbx.files_upload(f.read(), dropbox_path, mode=dropbox.files.WriteMode("overwrite"))

        # Create or reuse a shared link
        links = dbx.sharing_list_shared_links(path=dropbox_path).links
        if links:
            url = links[0].url
        else:
            url = dbx.sharing_create_shared_link_with_settings(dropbox_path).url

        return url.replace("?dl=0", "?dl=1")  # direct download link
    except Exception as e:
        print("❌ Dropbox upload error:", e)
        return None


@app.get("/")
def root():
    return {"status": "running"}


@app.post("/process")
async def process_video(request: Request):
    data = await request.json()
    job_id = data.get("job_id", "default_job")
    file_url = data.get("file_url")

    print(f"🎬 Received job: {job_id}")
    print(f"Downloading video from: {file_url}")

    try:
        os.makedirs("downloads", exist_ok=True)

        # Download video
        ydl_opts = {
            'outtmpl': f'downloads/{job_id}.mp4',
            'quiet': True,
            'format': 'best[ext=mp4]/best'
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([file_url])

        input_path = f"downloads/{job_id}.mp4"
        print(f"✅ Downloaded: {input_path}")

        # Process clips
        video = VideoFileClip(input_path)
        duration = video.duration
        os.makedirs(f"downloads/{job_id}_clips", exist_ok=True)

        clip_links = []
        for i in range(3):
            start = random.uniform(0, max(1, duration - 5))
            end = min(duration, start + random.uniform(2, 4))
            clip = video.subclip(start, end)
            clip_path = f"downloads/{job_id}_clips/clip_{i+1}.mp4"
            clip.write_videofile(
                clip_path, codec="libx264", audio_codec="aac", verbose=False, logger=None
            )

            # Upload each clip to Dropbox 👇
            dropbox_path = f"/{job_id}_clips/clip_{i+1}.mp4"
            link = upload_to_dropbox(clip_path, dropbox_path)
            if link:
                clip_links.append(link)

        print(f"✅ Finished and uploaded {len(clip_links)} clips for {job_id}")
        return {"status": "completed", "links": clip_links}

    except Exception as e:
        print("❌ Error:", e)
        return {"status": "error", "message": str(e)}
