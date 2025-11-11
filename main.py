from fastapi import FastAPI, Request
import asyncio
import os
import random
from moviepy.editor import VideoFileClip
import yt_dlp
import dropbox
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# Initialize Dropbox client (reads from Render environment variable)
DROPBOX_TOKEN = os.getenv("DROPBOX_TOKEN")
dbx = dropbox.Dropbox(DROPBOX_TOKEN) if DROPBOX_TOKEN else None

app.mount("/downloads", StaticFiles(directory="downloads"), name="downloads")

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
        ydl_opts = {
            'outtmpl': f'downloads/{job_id}.mp4',
            'quiet': True,
            'format': 'best[ext=mp4]/best'
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([file_url])

        input_path = f"downloads/{job_id}.mp4"
        print(f"✅ Downloaded: {input_path}")

        video = VideoFileClip(input_path)
        duration = video.duration
        os.makedirs(f"downloads/{job_id}_clips", exist_ok=True)

        clip_paths = []
        dropbox_links = []

        for i in range(3):
            start = random.uniform(0, max(1, duration - 5))
            end = min(duration, start + random.uniform(2, 4))
            clip = video.subclip(start, end)
            clip_path = f"downloads/{job_id}_clips/clip_{i+1}.mp4"
            clip.write_videofile(clip_path, codec="libx264", audio_codec="aac", verbose=False, logger=None)
            clip_paths.append(clip_path)

            # Upload to Dropbox if configured
            if dbx:
                dropbox_dest = f"/video_clips/{os.path.basename(clip_path)}"
                with open(clip_path, "rb") as f:
                    dbx.files_upload(f.read(), dropbox_dest, mode=dropbox.files.WriteMode("overwrite"))
                shared_link = dbx.sharing_create_shared_link_with_settings(dropbox_dest).url
                dropbox_links.append(shared_link)

        print(f"✅ Finished {len(clip_paths)} clips for {job_id}")
        return {"status": "completed", "dropbox_links": dropbox_links}

    except Exception as e:
        print("❌ Error:", e)
        return {"status": "error", "message": str(e)}
