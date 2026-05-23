#!/usr/bin/env python3
"""FastAPI backend for previz-ai-asisted-storyboard on fly.io.

Endpoints:
  GET  /                    → index.html
  GET  /story               → story.json (from Azure or local)
  POST /save-story          → save story.json to Azure per-story container
  POST /generate            → submit generation job (server-side API key)
  GET  /status/{job_id}     → poll job status
  GET  /images/{story}/{filename} → redirect to Azure Blob Storage
  POST /gemini              → call Gemini API for chat/flash responses
  GET  /health              → health check
"""

import json
import os
import time
import base64
import re
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


# Job ID → filename mapping (in-memory for single-machine state)
_job_filenames: dict[str, str] = {}
# Current active story container
_current_story_container: str = "story-rifat"


def _ensure_container(container: str) -> None:
    """Create container if it doesn't exist."""
    if not blob_service:
        return
    try:
        blob_service.create_container(container, public_access="blob")
    except Exception:
        pass  # Already exists


def _get_story_container(story_id: str | None = None) -> str:
    """Return container name for a story."""
    global _current_story_container
    if story_id:
        _current_story_container = story_id
    return _current_story_container


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


def save_image_to_azure(data: dict, filename: str, container: str | None = None) -> str:
    if not blob_service:
        raise RuntimeError("Azure Blob Storage not configured")

    container = container or _get_story_container()
    _ensure_container(container)

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
    blob_client = blob_service.get_blob_client(container=container, blob=filename)
    blob_client.upload_blob(image_data, overwrite=True, content_settings=ContentSettings(content_type="image/png"))

    return f"https://{AZURE_STORAGE_ACCOUNT}.blob.core.windows.net/{container}/{filename}"


@app.get("/", response_class=HTMLResponse)
def read_index():
    index_path = BASE_DIR / "index.html"
    if index_path.exists():
        return index_path.read_text(encoding="utf-8")
    return HTMLResponse(content="<h1>AI Storyboard Generator</h1><p>index.html not found</p>")


@app.get("/story")
def read_story(story: str | None = None):
    """Read story.json from Azure if available, otherwise local."""
    container = _get_story_container(story)

    # Try Azure first
    if blob_service:
        try:
            blob_client = blob_service.get_blob_client(container=container, blob="story.json")
            data = json.loads(blob_client.download_blob().readall().decode("utf-8"))
            data["_source"] = "azure"
            data["_container"] = container
            return JSONResponse(content=data)
        except Exception:
            pass  # Fall through to local

    # Fallback to local
    story_path = DATA_DIR / "story.json"
    if not story_path.exists():
        raise HTTPException(status_code=404, detail="story.json not found")
    local_data = json.loads(story_path.read_text(encoding="utf-8"))
    local_data["_source"] = "local"
    local_data["_container"] = container
    return JSONResponse(content=local_data)


@app.post("/save-story")
def save_story(body: dict) -> dict:
    """Save story.json to Azure per-story container."""
    if not blob_service:
        raise HTTPException(status_code=500, detail="Azure Blob Storage not configured")

    story_id = body.get("story_id", "story-rifat")
    story_data = body.get("story", {})

    container = _get_story_container(story_id)
    _ensure_container(container)

    blob_client = blob_service.get_blob_client(container=container, blob="story.json")
    blob_client.upload_blob(
        json.dumps(story_data, indent=2, ensure_ascii=False).encode("utf-8"),
        overwrite=True,
        content_settings=ContentSettings(content_type="application/json"),
    )

    return {"saved": True, "container": container, "blob": "story.json"}


@app.get("/stories")
def list_stories() -> dict:
    """List all story containers in Azure."""
    if not blob_service:
        return {"stories": []}

    stories = []
    for container in blob_service.list_containers():
        name = container.name
        if name.startswith("story-"):
            stories.append(name)

    return {"stories": sorted(stories)}


@app.post("/generate")
def generate(body: dict) -> dict:
    if not RUNPOD_API_KEY:
        raise HTTPException(status_code=500, detail="RUNPOD_API_KEY not configured")

    prompt = body.get("prompt", "")
    filename = body.get("filename", "generated.png")
    story_id = body.get("story_id", "story-rifat")

    # Set current story context
    _get_story_container(story_id)

    result = runpod_submit(prompt)
    job_id = result.get("id")
    if not job_id:
        raise HTTPException(status_code=500, detail="No job ID from RunPod")

    _job_filenames[job_id] = filename

    return {"job_id": job_id, "filename": filename, "status": result.get("status", "UNKNOWN")}


@app.get("/status/{job_id}")
def status(job_id: str) -> dict:
    if not RUNPOD_API_KEY:
        raise HTTPException(status_code=500, detail="RUNPOD_API_KEY not configured")

    data = runpod_poll(job_id)
    state = data.get("status", "UNKNOWN")

    if state == "COMPLETED":
        filename = _job_filenames.get(job_id, f"{job_id}.png")
        try:
            url = save_image_to_azure(data, filename)
            data["saved_url"] = url
            data["saved_file"] = filename
            del _job_filenames[job_id]
        except Exception as exc:
            data["save_error"] = str(exc)

    return data


@app.get("/images/{story}/{filename}")
def serve_image(story: str, filename: str):
    """Redirect to Azure Blob Storage per-story container."""
    if not AZURE_STORAGE_ACCOUNT:
        raise HTTPException(status_code=500, detail="Azure Storage not configured")
    url = f"https://{AZURE_STORAGE_ACCOUNT}.blob.core.windows.net/{story}/{filename}"
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


@app.get("/{page}.html", response_class=HTMLResponse)
def read_page(page: str):
    page_path = BASE_DIR / f"{page}.html"
    if page_path.exists():
        return page_path.read_text(encoding="utf-8")
    raise HTTPException(status_code=404, detail=f"{page}.html not found")


@app.get("/md/{path:path}")
def serve_markdown(path: str):
    """Serve markdown files for the docs viewer."""
    file_path = BASE_DIR / path
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    content = file_path.read_text(encoding="utf-8")
    return JSONResponse(content={"content": content})


@app.get("/health")
def health():
    return {
        "status": "ok",
        "endpoint": RUNPOD_ENDPOINT,
        "storage": AZURE_STORAGE_ACCOUNT if blob_service else "not configured",
        "gemini": "configured" if GEMINI_API_KEY else "not configured",
    }
