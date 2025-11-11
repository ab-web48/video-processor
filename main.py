from fastapi import FastAPI, Request
import asyncio
import os
import random
from moviepy.editor import VideoFileClip
import yt_dlp

app = FastAPI()

@app.get("/")
def root():
    return {"status": "running"}

@app.post("/process")
async def process_video(request: Request):
    data = await request.json()
    job_id = data.get("job_id")
    file_url = data.get("file_url")

    print(f"🎬 Received job: {job_id}")
    print(f"Downloading video from: {file_url}")

    try:
        # Create folder
        os.makedirs("downloads", exist_ok=True)

        # Download the YouTube video
        ydl_opts = {
            'outtmpl': f'downloads/{job_id}.mp4',
            'quiet': True,
            'format': 'best[ext=mp4]/best'
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([file_url])

        input_path = f"downloads/{job_id}.mp4"
        print(f"✅ Downloaded: {input_path}")

        # Open video and get duration
        video = VideoFileClip(input_path)
        duration = video.duration

        # Make 10 random clips, 3–5 seconds each
        os.makedirs(f"downloads/{job_id}_clips", exist_ok=True)
        clip_paths = []
        for i in range(10):
            start = random.uniform(0, max(1, duration - 6))
            end = min(duration, start + random.uniform(3, 5))
            clip = video.subclip(start, end)
            clip_path = f"downloads/{job_id}_clips/clip_{i+1}.mp4"
            clip.write_videofile(clip_path, codec="libx264", audio_codec="aac", verbose=False, logger=None)
            clip_paths.append(clip_path)

        print(f"✅ Created {len(clip_paths)} clips for job {job_id}")
        video.close()

        return {"status": "completed", "job_id": job_id, "clips": clip_paths}

    except Exception as e:
        print(f"❌ Error processing video: {e}")
        return {"status": "error", "message": str(e)}
