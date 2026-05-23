#!/usr/bin/env python3
"""FastAPI backend for previz-ai-asisted-storyboard on fly.io.

Endpoints:
  GET  /                    → index.html
  GET  /story               → story.json
  POST /generate            → submit generation job (server-side API key)
  GET  /status/{job_id}     → poll job status
  GET  /images/{filename}   → serve generated PNG
"""

import json
import os
import time
import base64
import urllib.request
from pathlib import Path
from urllib.error import HTTPError

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="AI Storyboard Generator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output" / "generated"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR = BASE_DIR / "data"

RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY", "")
RUNPOD_ENDPOINT = os.getenv("RUNPOD_ENDPOINT_ID", "b6cpv4fbec236e")


def runpod_submit(prompt: str) -> dict:
    url = f"https://api.runpod.ai/v2/{RUNPOD_ENDPOINT}/run"
    payload = {
        "input": {
            "prompt": prompt,
            "negative_prompt": (
                "blurry, very low quality, deformed, ugly, text, watermark, signature, "
                "extra limbs, distorted face, bad anatomy, duplicate, mutation"
            ),
            "height": 1024,
            "width": 1024,
            "num_inference_steps": 40,
            "refiner_inference_steps": 50,
            "guidance_scale": 10.0,
            "strength": 0.75,
            "high_noise_frac": 0.7,
            "seed": -1,
            "scheduler": "K_EULER",
            "num_images": 1,
            "image_url": None,
        }
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {RUNPOD_API_KEY}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8")
        raise HTTPException(status_code=exc.code, detail=body)


def runpod_poll(job_id: str) -> dict:
    url = f"https://api.runpod.ai/v2/{RUNPOD_ENDPOINT}/status/{job_id}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {RUNPOD_API_KEY}"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def extract_and_save(data: dict, filename: str) -> str:
    candidates = []
    output = data.get("output", {})
    if isinstance(output, dict):
        if "image_url" in output and isinstance(output["image_url"], str):
            candidates.append(output["image_url"])
        if "images" in output and isinstance(output["images"], list):
            for img in output["images"]:
                if isinstance(img, str):
                    candidates.append(img)
    if not candidates:
        raise RuntimeError("No image data found.")

    image_data = base64.b64decode(candidates[0].split(",", 1)[1])
    out_path = OUTPUT_DIR / filename
    out_path.write_bytes(image_data)
    return str(out_path)


@app.get("/", response_class=HTMLResponse)
def read_index():
    index_path = BASE_DIR / "index.html"
    if index_path.exists():
        return index_path.read_text(encoding="utf-8")
    return HTMLResponse(content="<h1>AI Storyboard Generator</h1><p>index.html not found</p>")


@app.get("/story")
def read_story():
    story_path = DATA_DIR / "story.json"
    if not story_path.exists():
        raise HTTPException(status_code=404, detail="story.json not found")
    return JSONResponse(content=json.loads(story_path.read_text(encoding="utf-8")))


@app.post("/generate")
def generate(body: dict) -> dict:
    if not RUNPOD_API_KEY:
        raise HTTPException(status_code=500, detail="RUNPOD_API_KEY not configured")

    prompt = body.get("prompt", "")
    filename = body.get("filename", "generated.png")

    result = runpod_submit(prompt)
    job_id = result.get("id")
    if not job_id:
        raise HTTPException(status_code=500, detail="No job ID from RunPod")

    return {"job_id": job_id, "filename": filename, "status": result.get("status", "UNKNOWN")}


@app.get("/status/{job_id}")
def status(job_id: str) -> dict:
    if not RUNPOD_API_KEY:
        raise HTTPException(status_code=500, detail="RUNPOD_API_KEY not configured")

    data = runpod_poll(job_id)
    state = data.get("status", "UNKNOWN")

    # Auto-save image if completed
    if state == "COMPLETED":
        filename = data.get("input", {}).get("filename", f"{job_id}.png")
        try:
            extract_and_save(data, filename)
            data["saved_file"] = filename
        except Exception as exc:
            data["save_error"] = str(exc)

    return data


@app.get("/images/{filename}")
def serve_image(filename: str):
    img_path = OUTPUT_DIR / filename
    if not img_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(img_path, media_type="image/png")


@app.get("/health")
def health():
    return {"status": "ok", "endpoint": RUNPOD_ENDPOINT}
