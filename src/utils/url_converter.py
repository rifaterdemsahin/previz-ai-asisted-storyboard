#!/usr/bin/env python3
"""Convert various image hosting URLs to RunPod-compatible direct image URLs.

Usage (from project root):
    python3 src/utils/url_converter.py "https://drive.google.com/file/d/FILE_ID/view"
"""

import argparse
import sys
from urllib.parse import urlparse, parse_qs


def convert_google_drive(url: str) -> str | None:
    """Convert a Google Drive share/view URL to a direct download URL."""
    if "drive.google.com" not in url:
        return None
    file_id = None
    if "/d/" in url:
        parts = url.split("/d/")
        if len(parts) > 1:
            file_id = parts[1].split("/")[0].split("?")[0]
    elif "id=" in url:
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        if "id" in qs:
            file_id = qs["id"][0]
    if file_id:
        return f"https://drive.google.com/uc?export=view&id={file_id}"
    return None


def convert_dropbox(url: str) -> str | None:
    """Convert Dropbox share link to direct download by replacing dl=0 with dl=1."""
    if "dropbox.com" not in url and "dropboxusercontent.com" not in url:
        return None
    if "dl=0" in url:
        return url.replace("dl=0", "dl=1")
    if "?" not in url and "dropbox.com" in url:
        return url + "?dl=1"
    return url


def test_direct_url(url: str) -> str:
    """Print a curl command to verify the URL returns an image."""
    return f'curl -I "{url}" | grep -i content-type'


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert image hosting URLs to RunPod-compatible direct URLs."
    )
    parser.add_argument("url", help="The share URL from Google Drive, Dropbox, etc.")
    args = parser.parse_args()

    url = args.url.strip()
    result = None
    source = ""

    if "drive.google.com" in url:
        result = convert_google_drive(url)
        source = "Google Drive"
    elif "dropbox" in url:
        result = convert_dropbox(url)
        source = "Dropbox"
    elif "i.imgur.com" in url or "imgur.com" in url:
        result = url
        source = "Imgur"
    elif "raw.githubusercontent.com" in url:
        result = url
        source = "GitHub Raw"
    else:
        print("Unknown hosting provider. If the URL ends in .jpg/.png and serves raw bytes, it may already work.")
        result = url
        source = "Unknown"

    if result:
        print(f"\n{source} → RunPod direct URL:\n{result}\n")
        print("Verify it serves raw image bytes with:")
        print(f"  {test_direct_url(result)}")
        print("\nExpected output: Content-Type: image/jpeg  or  image/png")
        print("\nUse this URL as image_url in your RunPod payload.")
    else:
        print("Could not convert URL. Please provide a shareable link.", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
