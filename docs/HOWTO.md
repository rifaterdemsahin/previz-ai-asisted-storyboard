# How to Run – Story Image Generator

## Prerequisites

- Python 3.10+ (no external pip packages required).
- A RunPod API key stored in `config/.env`:
  ```bash
  echo "RUNPOD_API_KEY=your_key_here" > config/.env
  ```

## Folder Quick-Start

```bash
mkdir -p config data output/generated input/raw
```

## Generating Story Images

### 1. Generate all chapters at once

```bash
python3 src/generators/batch.py
```

**Output:** `output/generated/txt2img_ch01_the_discovery.png` through `txt2img_ch09_the_certificate.png`

### 2. Generate a single chapter

```bash
python3 src/generators/single.py 3
# Generates Chapter 3: Kusadasi
```

### 3. Generate Chapter 1 only (quick test)

```bash
python3 src/generators/chapter_one.py
```

### 4. Skip already-generated chapters

```bash
python3 src/generators/batch.py --skip-existing
```

### 5. Use a seed image (img2img mode)

```bash
python3 src/generators/single.py 1 --mode seeded --strength 0.65
```

## Base64 Image Converter

If the RunPod API returns base64-encoded JSON instead of direct image URLs:

```bash
# From a JSON response file
python3 src/utils/base64_to_image.py -f input/raw/runpod_response.json

# Pipe via stdin
cat input/raw/runpod_response.json | python3 src/utils/base64_to_image.py

# Custom output path
python3 src/utils/base64_to_image.py -f input/raw/response.json -o output/generated/my_image.png
```

**Output:** Images are saved to `output/generated/` by default.

## Utility Scripts

### URL Converter

Convert Google Drive or Dropbox share links to RunPod-compatible direct URLs:

```bash
python3 src/utils/url_converter.py "https://drive.google.com/file/d/FILE_ID/view"
```

### Image to Base64

Convert a local seed image to a base64 data URI:

```bash
python3 src/utils/image_to_base64.py input/raw/seed.png -o input/raw/seed_b64.txt
```

### RunPod Test Query

Send a quick test prompt to the RunPod endpoint:

```bash
python3 scripts/runpod_query.py
```

Saves the raw JSON response to `input/raw/runpod_{job_id}.json`.

## Optional Flags

| Flag | Description |
|------|-------------|
| `--mode {seeded,txt2img}` | Switch between img2img (seeded) and pure txt2img generation. |
| `--strength FLOAT` | img2img strength 0.0–1.0 (default 0.75). Only applies to seeded mode. |
| `--endpoint ID` | Override the RunPod endpoint ID. |
| `--out DIR` | Change the output directory (default: `output/generated`). |
| `--skip-existing` | Skip chapters whose output file already exists. |

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `RUNPOD_API_KEY not found` | Add the key to `config/.env` or export it as an environment variable. |
| `data/story.json not found` | Ensure the story data file is in the `data/` directory. |
| Job stuck in `IN_QUEUE` for > 10 min | The endpoint may be overloaded. Cancel and retry, or switch endpoints. |
| `No image data found` | The API response format may have changed. Check `input/raw/` JSON for fields. |

## Related Files

- `src/generators/batch.py` — Batch chapter generation.
- `src/generators/single.py` — Single chapter generation.
- `src/shared/runpod_client.py` — Shared RunPod API client.
- `config/.env` — API credentials.
- `docs/AGENTS.md` — Project conventions and context.
