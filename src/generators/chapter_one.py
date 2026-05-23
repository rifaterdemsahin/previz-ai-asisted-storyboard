#!/usr/bin/env python3
"""Generate Chapter 1 image only.

Usage (from project root):
    python3 src/generators/chapter_one.py
"""

import json
import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.shared.env import load_env
from src.shared.runpod_client import runpod_generate, poll_status, extract_image


def main() -> int:
    env = load_env()
    api_key = env.get("RUNPOD_API_KEY", os.getenv("RUNPOD_API_KEY"))
    if not api_key:
        print("Error: RUNPOD_API_KEY not found in config/.env or env.", file=sys.stderr)
        return 1

    endpoint_id = env.get("RUNPOD_ENDPOINT_ID", "b6cpv4fbec236e")

    story = json.loads(Path("data/story.json").read_text(encoding="utf-8"))
    chapter = story["chapters"][0]
    prompt = chapter["image_prompt"]
    title = chapter["title"].lower().replace(" ", "_")
    out_file = f"output/generated/story_ch01_{title}.png"

    print(f"Generating Chapter 1: {chapter['title']}")
    print(f"Prompt: {prompt}")
    print(f"Submitting to RunPod endpoint {endpoint_id}...")

    result = runpod_generate(prompt, None, api_key, endpoint_id)
    job_id = result.get("id")
    if not job_id:
        print("Error: no job ID returned.", file=sys.stderr)
        return 1

    print(f"Job {job_id} queued. Waiting for completion...")
    while True:
        time.sleep(10)
        status = poll_status(job_id, api_key, endpoint_id)
        state = status.get("status", "UNKNOWN")
        print(f"  Status: {state}")
        if state == "COMPLETED":
            extract_image(status, out_file)
            print(f"Saved image: {out_file}")
            break
        if state in ("FAILED", "CANCELLED", "TIMED_OUT"):
            print(f"Job failed with status: {state}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
