#!/usr/bin/env python3
"""Helper script to update story.json chapters.

Usage:
    python3 update_story.py --chapter 3 --title "New Title" --text "New text..." --prompt "New prompt..."
    python3 update_story.py --chapter 5 --file new_chapter.json
"""

import argparse
import json
from pathlib import Path


def load_story():
    path = Path("data/story.json")
    return json.loads(path.read_text(encoding="utf-8"))


def save_story(story):
    path = Path("data/story.json")
    path.write_text(json.dumps(story, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Saved: {path}")


def update_chapter(story, chapter_num, title=None, setting=None, text=None, prompt=None):
    for ch in story["chapters"]:
        if ch.get("chapter") == chapter_num:
            if title: ch["title"] = title
            if setting: ch["setting"] = setting
            if text: ch["text"] = text
            if prompt: ch["image_prompt"] = prompt
            print(f"Updated Chapter {chapter_num}: {ch['title']}")
            return True
    print(f"Chapter {chapter_num} not found")
    return False


def main():
    parser = argparse.ArgumentParser(description="Update story.json chapters")
    parser.add_argument("--chapter", type=int, required=True)
    parser.add_argument("--title")
    parser.add_argument("--setting")
    parser.add_argument("--text")
    parser.add_argument("--prompt", help="Image prompt")
    parser.add_argument("--file", help="JSON file with chapter updates")
    args = parser.parse_args()

    story = load_story()

    if args.file:
        updates = json.loads(Path(args.file).read_text(encoding="utf-8"))
        update_chapter(story, args.chapter, **updates)
    else:
        update_chapter(story, args.chapter, args.title, args.setting, args.text, args.prompt)

    save_story(story)


if __name__ == "__main__":
    main()
