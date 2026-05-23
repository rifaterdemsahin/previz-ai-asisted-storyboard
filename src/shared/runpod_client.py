import base64
import json
import os
import urllib.request
from pathlib import Path
from urllib.error import HTTPError


def runpod_generate(
    prompt: str,
    image_url: str | None,
    api_key: str,
    endpoint_id: str,
    strength: float = 0.75,
) -> dict:
    """Submit a generation job to the RunPod Serverless API."""
    url = f"https://api.runpod.ai/v2/{endpoint_id}/run"
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
            "strength": strength,
            "high_noise_frac": 0.7,
            "seed": -1,
            "scheduler": "K_EULER",
            "num_images": 1,
            "image_url": image_url,
        }
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8")
        raise RuntimeError(f"RunPod API error {exc.code}: {body}") from exc


def poll_status(job_id: str, api_key: str, endpoint_id: str) -> dict:
    """Poll the status of a RunPod job."""
    url = f"https://api.runpod.ai/v2/{endpoint_id}/status/{job_id}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key}"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def extract_image(data: dict, out_path: str) -> str:
    """Extract base64 image data from a completed RunPod job response and save to file."""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
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
    seen = set()
    unique = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            unique.append(c)
    image_data = base64.b64decode(unique[0].split(",", 1)[1])
    with open(out_path, "wb") as f:
        f.write(image_data)
    return out_path
