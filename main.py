from fastapi import FastAPI, Request
import asyncio

app = FastAPI()

@app.get("/")
def root():
    return {"status": "running"}

@app.post("/process")
async def process_video(request: Request):
    data = await request.json()
    print("Received job:", data)
    await asyncio.sleep(5)
    print("Finished processing video for job:", data.get("job_id"))
    return {"status": "completed", "job_id": data.get("job_id")}
