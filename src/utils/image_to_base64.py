#!/usr/bin/env python3
"""Convert an image file to a base64 data URI for use as RunPod image_url seed.

Usage (from project root):
    python3 src/utils/image_to_base64.py input/raw/seed.png
    python3 src/utils/image_to_base64.py input/raw/seed.png -o input/raw/seed_b64.txt
"""

import argparse
import base64
import os
import sys
from pathlib import Path


def image_to_data_uri(image_path: str) -> str:
    """Read an image file and return a data:image/...;base64,... URI."""
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    data = path.read_bytes()
    ext = path.suffix.lower()

    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }
    mime = mime_map.get(ext, "image/png")
    b64 = base64.b64encode(data).decode("utf-8")
    return f"data:{mime};base64,{b64}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert an image to a base64 data URI and optionally save to a text file."
    )
    parser.add_argument("image", help="Path to the seed image.")
    parser.add_argument(
        "-o", "--output", help="Output text file path (optional). Prints to stdout if omitted."
    )
    args = parser.parse_args()

    try:
        uri = image_to_data_uri(args.image)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(uri, encoding="utf-8")
        size_kb = len(uri) / 1024
        print(f"Saved data URI to: {args.output} ({size_kb:.1f} KB)")
    else:
        print(uri)

    return 0


if __name__ == "__main__":
    sys.exit(main())
