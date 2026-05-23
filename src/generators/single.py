#!/usr/bin/env python3
"""Generate a single story chapter image with scene-first prompting.

Usage (from project root):
    python3 src/generators/single.py 1
    python3 src/generators/single.py 5 --mode seeded --strength 0.65
"""

import argparse
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
    parser = argparse.ArgumentParser(
        description="Generate a single story chapter with improved prompting."
    )
    parser.add_argument(
        "chapter", nargs="?", type=int, default=1,
        help="Chapter number to generate (default: 1)."
    )
    parser.add_argument(
        "--strength", type=float, default=0.75,
        help="img2img strength 0.0-1.0 (default: 0.75). Only used in seeded mode."
    )
    parser.add_argument(
        "--endpoint", default="b6cpv4fbec236e",
        help="RunPod endpoint ID."
    )
    parser.add_argument(
        "--out", default="output/generated",
        help="Output directory (default: output/generated)."
    )
    parser.add_argument(
        "--mode", choices=["seeded", "txt2img"], default="txt2img",
        help="Generation mode. 'seeded' uses a portrait seed. 'txt2img' generates from prompt only. (default: txt2img)"
    )
    args = parser.parse_args()

    env = load_env()
    api_key = env.get("RUNPOD_API_KEY", os.getenv("RUNPOD_API_KEY"))
    if not api_key:
        print("Error: RUNPOD_API_KEY not found in config/.env or env.", file=sys.stderr)
        return 1

    endpoint_id = env.get("RUNPOD_ENDPOINT_ID", args.endpoint)

    story_path = Path("data/story.json")
    if not story_path.exists():
        print("Error: data/story.json not found.", file=sys.stderr)
        return 1

    story = json.loads(story_path.read_text(encoding="utf-8"))
    chapters = story.get("chapters", [])
    seed_url = story.get("seed_image_url")

    if args.chapter < 1 or args.chapter > len(chapters):
        print(f"Error: chapter {args.chapter} not found (1–{len(chapters)}).", file=sys.stderr)
        return 1

    chapter = chapters[args.chapter - 1]
    original_prompt = chapter.get("image_prompt", "")
    title = chapter.get("title", f"chapter_{args.chapter}")
    safe_title = title.lower().replace(" ", "_").replace("'", "")
    out_file = f"{args.out}/{args.mode}_ch{args.chapter:02d}_{safe_title}.png"

    seed_url = seed_url if args.mode == "seeded" else None

    print(f"\nChapter {args.chapter}: {title}")
    print(f"Mode: {args.mode}")
    print(f"Prompt:\n  {original_prompt}\n")
    if seed_url:
        print(f"Seed URL: {seed_url}")
    print(f"Strength: {args.strength}")
    print(f"Submitting to RunPod endpoint {endpoint_id}...")

    result = runpod_generate(original_prompt, seed_url, api_key, endpoint_id, args.strength)
    job_id = result.get("id")
    if not job_id:
        print("Error: no job ID returned.", file=sys.stderr)
        return 1

    print(f"Job {job_id} queued. Waiting for completion...")
    while True:
        time.sleep(15)
        status = poll_status(job_id, api_key, endpoint_id)
        state = status.get("status", "UNKNOWN")
        print(f"  Status: {state}")
        if state == "COMPLETED":
            extract_image(status, out_file)
            size_kb = Path(out_file).stat().st_size / 1024
            print(f"\nSaved image: {out_file} ({size_kb:.0f} KB)")
            break
        if state in ("FAILED", "CANCELLED", "TIMED_OUT"):
            print(f"Job failed with status: {state}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
