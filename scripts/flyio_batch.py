#!/usr/bin/env python3
"""Trigger batch generation via fly.io backend and poll for completion."""

import json
import time
import urllib.request

BASE_URL = "https://previz-ai-storyboard.fly.dev"
STORY_PATH = "data/story.json"

def load_story():
    with open(STORY_PATH, encoding="utf-8") as f:
        return json.load(f)

def submit_chapter(prompt: str, filename: str) -> dict:
    payload = json.dumps({"prompt": prompt, "filename": filename}).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

def poll_status(job_id: str) -> dict:
    req = urllib.request.Request(f"{BASE_URL}/status/{job_id}", method="GET")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

def safe_filename(title: str, idx: int) -> str:
    safe = title.lower().replace(" ", "_").replace("'", "")
    return f"txt2img_ch{idx:02d}_{safe}.png"

def main():
    story = load_story()
    chapters = story.get("chapters", [])
    jobs = []

    print(f"Submitting {len(chapters)} chapters to {BASE_URL}...\n")

    for i, ch in enumerate(chapters, start=1):
        title = ch.get("title", f"chapter_{i}")
        prompt = ch.get("image_prompt", "")
        filename = safe_filename(title, i)

        try:
            result = submit_chapter(prompt, filename)
            job_id = result.get("job_id")
            print(f"Chapter {i}: {title} → job {job_id}")
            jobs.append({"chapter": i, "title": title, "job_id": job_id, "filename": filename})
        except Exception as exc:
            print(f"Chapter {i}: FAILED to submit — {exc}")

    if not jobs:
        print("\nNo jobs submitted. Exiting.")
        return

    print(f"\nPolling {len(jobs)} jobs every 15s...\n")
    pending = set(j["job_id"] for j in jobs)

    while pending:
        time.sleep(15)
        for job in list(jobs):
            jid = job["job_id"]
            if jid not in pending:
                continue
            try:
                status = poll_status(jid)
                state = status.get("status", "UNKNOWN")
                if state == "COMPLETED":
                    url = status.get("saved_url", "saved")
                    print(f"  ✓ Chapter {job['chapter']}: COMPLETED → {url}")
                    pending.remove(jid)
                elif state in ("FAILED", "CANCELLED", "TIMED_OUT"):
                    print(f"  ✗ Chapter {job['chapter']}: {state}")
                    pending.remove(jid)
                else:
                    print(f"  ○ Chapter {job['chapter']}: {state}")
            except Exception as exc:
                print(f"  ! Chapter {job['chapter']}: poll error — {exc}")

    print("\nBatch generation complete.")

if __name__ == "__main__":
    main()
