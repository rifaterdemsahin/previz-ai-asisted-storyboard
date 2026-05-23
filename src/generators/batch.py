#!/usr/bin/env python3
"""Batch-generate all story chapter images.

Usage (from project root):
    python3 src/generators/batch.py
    python3 src/generators/batch.py --mode seeded --skip-existing
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
        description="Batch-generate all story chapter images."
    )
    parser.add_argument(
        "--mode", choices=["seeded", "txt2img"], default="txt2img",
        help="Generation mode. 'seeded' uses a portrait seed. 'txt2img' generates from prompt only. (default: txt2img)"
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
        "--skip-existing", action="store_true",
        help="Skip chapters whose output file already exists."
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

    seed_url = seed_url if args.mode == "seeded" else None
    if args.mode == "seeded" and not seed_url:
        print("Warning: no seed_image_url in data/story.json. Generating without seed.")
    elif args.mode == "seeded":
        print(f"Using seed image: {seed_url}")

    print(f"\nGenerating {len(chapters)} chapters (mode={args.mode}, endpoint={endpoint_id})...")
    print("=" * 60)

    for idx, chapter in enumerate(chapters, start=1):
        title = chapter.get("title", f"chapter_{idx}")
        prompt = chapter.get("image_prompt", "")
        safe_title = title.lower().replace(" ", "_").replace("'", "")
        out_file = f"{args.out}/{args.mode}_ch{idx:02d}_{safe_title}.png"

        if args.skip_existing and Path(out_file).exists():
            print(f"\nChapter {idx}: {title} — ALREADY EXISTS ({out_file})")
            continue

        print(f"\nChapter {idx}: {title}")
        print(f"  Prompt: {prompt[:100]}...")

        try:
            result = runpod_generate(prompt, seed_url, api_key, endpoint_id, args.strength)
            job_id = result.get("id")
            if not job_id:
                print("  Error: no job ID returned. Skipping.", file=sys.stderr)
                continue

            print(f"  Job {job_id} queued...")
            poll_count = 0
            while True:
                time.sleep(30)
                poll_count += 1
                status = poll_status(job_id, api_key, endpoint_id)
                state = status.get("status", "UNKNOWN")
                if state == "COMPLETED":
                    extract_image(status, out_file)
                    size_kb = Path(out_file).stat().st_size / 1024
                    print(f"  ✓ Saved: {out_file} ({size_kb:.0f} KB)")
                    break
                if state in ("FAILED", "CANCELLED", "TIMED_OUT"):
                    print(f"  ✗ Job failed: {state}", file=sys.stderr)
                    break
        except Exception as exc:
            print(f"  ✗ Error: {exc}", file=sys.stderr)
            continue

    print(f"\n{'=' * 60}")
    print("Batch generation complete.")
    print(f"\nOutput files in {args.out}:")
    for p in sorted(Path(args.out).glob(f"{args.mode}_ch*.png")):
        print(f"  {p.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
