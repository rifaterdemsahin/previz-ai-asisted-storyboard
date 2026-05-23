#!/usr/bin/env python3
"""Query RunPod Serverless API and save JSON responses to input/raw/.

Usage (from project root):
    python3 scripts/runpod_query.py
"""

import json
import os
import sys
import urllib.request
from pathlib import Path
from urllib.error import HTTPError

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.shared.env import load_env


def runpod_request(
    endpoint_id: str,
    payload: dict,
    api_key: str,
    operation: str = "run",
) -> dict:
    """Make a synchronous request to the RunPod Serverless API."""
    url = f"https://api.runpod.ai/v2/{endpoint_id}/{operation}"
    data = json.dumps({"input": payload}).encode("utf-8")
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


def save_response(data: dict, out_dir: str = "input/raw") -> Path:
    """Save API response JSON to the input/raw directory with a timestamped name."""
    os.makedirs(out_dir, exist_ok=True)
    job_id = data.get("id", "unknown")
    safe_id = job_id.replace("/", "_").replace(":", "_")
    path = Path(out_dir) / f"runpod_{safe_id}.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Saved response to: {path}")
    return path


def default_payload() -> dict:
    """Default Stable Diffusion XL payload."""
    return {
        "prompt": "a developer working on a laptop in a modern coffee shop, cinematic lighting, highly detailed",
        "negative_prompt": (
            "blurry, very low quality, deformed, ugly, text, watermark, signature"
        ),
        "height": 1024,
        "width": 1024,
        "num_inference_steps": 25,
        "refiner_inference_steps": 50,
        "guidance_scale": 7.5,
        "strength": 0.3,
        "high_noise_frac": 0.8,
        "seed": 1337,
        "scheduler": "K_EULER",
        "num_images": 1,
        "image_url": None,
    }


def main() -> int:
    env = load_env()
    api_key = env.get("RUNPOD_API_KEY", os.getenv("RUNPOD_API_KEY"))
    if not api_key or api_key == "YOUR_API_KEY_HERE":
        print(
            "Error: RUNPOD_API_KEY not set. Add it to config/.env or export it.",
            file=sys.stderr,
        )
        return 1

    endpoint_id = env.get("RUNPOD_ENDPOINT_ID", "b6cpv4fbec236e")
    payload = default_payload()

    print(f"Sending request to RunPod endpoint {endpoint_id}...")
    try:
        result = runpod_request(endpoint_id, payload, api_key)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2))
    save_response(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
