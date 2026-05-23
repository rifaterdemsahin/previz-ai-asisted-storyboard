#!/usr/bin/env python3
"""FastAPI backend for previz-ai-asisted-storyboard on fly.io.

Endpoints:
  GET  /                    → index.html
  GET  /story               → story.json
  POST /generate            → submit generation job (server-side API key)
  GET  /status/{job_id}     → poll job status
  GET  /images/{filename}   → redirect to Azure Blob Storage
  POST /gemini              → call Gemini API for chat/flash responses
  GET  /health              → health check
"""

import json
import os
import time
import base64
import urllib.request
from pathlib import Path
from urllib.error import HTTPError

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

from azure.storage.blob import BlobServiceClient, ContentSettings

app = FastAPI(title="AI Storyboard Generator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY", "")
RUNPOD_ENDPOINT = os.getenv("RUNPOD_ENDPOINT_ID", "b6cpv4fbec236e")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
AZURE_STORAGE_CONN = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
AZURE_STORAGE_ACCOUNT = os.getenv("AZURE_STORAGE_ACCOUNT", "dpstoryboardsa")
AZURE_CONTAINER = os.getenv("AZURE_CONTAINER", "images")

# Init Azure Blob client
blob_service = None
if AZURE_STORAGE_CONN:
    blob_service = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONN)


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


def save_image_to_azure(data: dict, filename: str) -> str:
    if not blob_service:
        raise RuntimeError("Azure Blob Storage not configured")

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
    blob_client = blob_service.get_blob_client(container=AZURE_CONTAINER, blob=filename)
    blob_client.upload_blob(image_data, overwrite=True, content_settings=ContentSettings(content_type="image/png"))

    return f"https://{AZURE_STORAGE_ACCOUNT}.blob.core.windows.net/{AZURE_CONTAINER}/{filename}"


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

    if state == "COMPLETED":
        filename = data.get("input", {}).get("filename", f"{job_id}.png")
        try:
            url = save_image_to_azure(data, filename)
            data["saved_url"] = url
            data["saved_file"] = filename
        except Exception as exc:
            data["save_error"] = str(exc)

    return data


@app.get("/images/{filename}")
def serve_image(filename: str):
    """Redirect to Azure Blob Storage public URL."""
    if not AZURE_STORAGE_ACCOUNT:
        raise HTTPException(status_code=500, detail="Azure Storage not configured")
    url = f"https://{AZURE_STORAGE_ACCOUNT}.blob.core.windows.net/{AZURE_CONTAINER}/{filename}"
    return RedirectResponse(url=url)


@app.post("/gemini")
def gemini_chat(body: dict) -> dict:
    """Proxy to Gemini API for chat/flash responses."""
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured")

    model = body.get("model", "gemini-2.0-flash")
    contents = body.get("contents", [])

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": contents,
        "generationConfig": body.get("generationConfig", {"temperature": 0.7, "maxOutputTokens": 2048}),
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8")
        raise HTTPException(status_code=exc.code, detail=body)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "endpoint": RUNPOD_ENDPOINT,
        "storage": AZURE_STORAGE_ACCOUNT if blob_service else "not configured",
        "gemini": "configured" if GEMINI_API_KEY else "not configured",
    }
