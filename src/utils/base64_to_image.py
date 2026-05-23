#!/usr/bin/env python3
"""Convert base64-encoded image data to image files.

Usage (from project root):
    python3 src/utils/base64_to_image.py -f input/raw/response.json
    cat input/raw/response.json | python3 src/utils/base64_to_image.py
"""

import argparse
import base64
import json
import os
import sys
from pathlib import Path


def detect_extension(data: bytes) -> str:
    """Detect image format from magic bytes."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data.startswith(b"\xff\xd8"):
        return ".jpg"
    if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
        return ".gif"
    if data.startswith(b"BM"):
        return ".bmp"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return ".webp"
    if data.startswith(b"\x00\x00\x01\x00") or data.startswith(b"\x00\x00\x02\x00"):
        return ".ico"
    return ".bin"


def base64_to_image(b64_string: str, output_path: str | None = None) -> str:
    """Convert a base64 string to an image file."""
    if "," in b64_string:
        b64_string = b64_string.split(",", 1)[1]
    b64_string = b64_string.strip()
    image_data = base64.b64decode(b64_string)

    if not output_path:
        ext = detect_extension(image_data)
        output_path = os.path.join("output", "generated", f"output_image{ext}")

    output_path = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "wb") as f:
        f.write(image_data)

    print(f"Saved image to: {output_path} ({len(image_data)} bytes)")
    return output_path


def extract_base64_from_text(text: str) -> list[str]:
    """Try to extract base64 image data from raw text or JSON."""
    candidates: list[str] = []
    stripped = text.strip()

    if stripped.startswith("{") or stripped.startswith("["):
        try:
            data = json.loads(stripped)
            def walk(obj):
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        if k in ("image_url", "images", "image", "url") and isinstance(v, str) and v.startswith("data:image"):
                            candidates.append(v)
                        elif k in ("image_url", "images", "image", "url") and isinstance(v, list):
                            for item in v:
                                if isinstance(item, str) and item.startswith("data:image"):
                                    candidates.append(item)
                        elif isinstance(v, (dict, list)):
                            walk(v)
                elif isinstance(obj, list):
                    for item in obj:
                        walk(item)
            walk(data)
        except json.JSONDecodeError:
            pass

    if not candidates:
        candidates = [stripped]

    return candidates


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert base64-encoded data to an image file."
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Base64 string, or path to a file containing base64 data. If omitted, reads from stdin.",
    )
    parser.add_argument("-o", "--output", help="Output image file path (optional).")
    parser.add_argument(
        "-f", "--file", action="store_true",
        help="Treat INPUT as a file path instead of raw base64 string.",
    )
    args = parser.parse_args()

    if args.file and args.input:
        input_path = Path(args.input)
        if not input_path.exists():
            fallback = Path("input/raw") / args.input
            if fallback.exists():
                input_path = fallback
            else:
                print(f"Error: file not found: {args.input}", file=sys.stderr)
                return 1
        b64_data = input_path.read_text(encoding="utf-8")
    elif args.input:
        b64_data = args.input
    else:
        print("Reading base64 data from stdin...", file=sys.stderr)
        b64_data = sys.stdin.read()

    if not b64_data.strip():
        print("Error: no base64 data provided.", file=sys.stderr)
        return 1

    candidates = extract_base64_from_text(b64_data)
    seen = set()
    unique_candidates = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            unique_candidates.append(c)
    candidates = unique_candidates
    if not candidates:
        print("Error: no base64 image data found.", file=sys.stderr)
        return 1

    default_stem = "output_image"
    if args.file and args.input:
        input_name = Path(args.input).name
        if input_name.endswith(".json"):
            default_stem = input_name[:-5]
        else:
            default_stem = Path(args.input).stem

    for idx, candidate in enumerate(candidates):
        out = args.output
        if len(candidates) > 1:
            if out:
                stem = Path(out).stem
                suffix = Path(out).suffix or ".png"
                out = f"{stem}_{idx}{suffix}"
            else:
                out = os.path.join("output", "generated", f"{default_stem}_{idx}.png")
        else:
            if not out:
                out = os.path.join("output", "generated", f"{default_stem}.png")
        try:
            base64_to_image(candidate, out)
        except Exception as exc:
            print(f"Error processing image {idx + 1}: {exc}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
