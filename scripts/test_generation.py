#!/usr/bin/env python3
"""Quick integration test: generate Chapter 1 and verify the image saves correctly.

Usage:
    python3 scripts/test_generation.py
"""
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.shared.env import load_env
from src.shared.runpod_client import runpod_generate, poll_status, extract_image


def main() -> int:
    env = load_env()
    api_key = env.get("RUNPOD_API_KEY", "")
    endpoint_id = "b6cpv4fbec236e"

    if not api_key or api_key == "your_runpod_api_key_here":
        print("Error: RUNPOD_API_KEY missing in config/.env", file=sys.stderr)
        return 1

    story = json.loads((PROJECT_ROOT / "data/story.json").read_text(encoding="utf-8"))
    chapter = story["chapters"][0]
    prompt = chapter["image_prompt"]
    title = chapter["title"].lower().replace(" ", "_").replace("'", "")
    out_file = str(PROJECT_ROOT / f"output/generated/test_ch01_{title}.png")

    print(f"Test: Generating Chapter 1 – {chapter['title']}")
    print(f"Endpoint: {endpoint_id}")
    print(f"Prompt: {prompt[:80]}...")
    print("Submitting...")

    result = runpod_generate(prompt, None, api_key, endpoint_id, strength=0.75)
    job_id = result.get("id")
    if not job_id:
        print("Error: no job ID returned", file=sys.stderr)
        return 1

    print(f"Job queued: {job_id}")
    print("Polling...")

    while True:
        time.sleep(15)
        status = poll_status(job_id, api_key, endpoint_id)
        state = status.get("status", "UNKNOWN")
        print(f"  {state}")
        if state == "COMPLETED":
            extract_image(status, out_file)
            size_kb = Path(out_file).stat().st_size / 1024
            print(f"\nSuccess: {out_file} ({size_kb:.0f} KB)")
            return 0
        if state in ("FAILED", "CANCELLED", "TIMED_OUT"):
            print(f"\nFailed: {state}", file=sys.stderr)
            return 1


if __name__ == "__main__":
    sys.exit(main())
