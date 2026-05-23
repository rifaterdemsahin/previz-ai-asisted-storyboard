# Agent Context – Story Image Generator

## Project Purpose

Generate chapter images for **"The Claude Code Certificate"** — a 9-chapter story about a developer named Alex learning Claude Code and earning his certification. Images are produced via the RunPod Serverless SDXL API.

## Folder Structure

```
├── config/
│   └── .env                     # RUNPOD_API_KEY, optional RUNPOD_ENDPOINT_ID
├── data/
│   └── story.json               # Chapter text and image_prompts
├── src/
│   ├── shared/
│   │   ├── env.py               # load_env("config/.env")
│   │   └── runpod_client.py     # runpod_generate, poll_status, extract_image
│   ├── generators/
│   │   ├── single.py            # Generate one chapter: python3 src/generators/single.py 3
│   │   ├── batch.py             # Generate all chapters: python3 src/generators/batch.py
│   │   └── chapter_one.py       # Generate Chapter 1 only
│   └── utils/
│       ├── base64_to_image.py   # Decode RunPod JSON responses to PNG
│       ├── url_converter.py     # Convert Google Drive/Dropbox URLs to direct links
│       └── image_to_base64.py   # Encode a local image to base64 data URI
├── scripts/
│   └── runpod_query.py          # Quick test query against RunPod endpoint
├── output/
│   └── generated/               # All generated chapter images land here
├── input/
│   └── raw/                     # Raw RunPod API JSON responses
├── docs/
│   ├── AGENTS.md                # This file
│   ├── HOWTO.md                 # CLI usage guide
│   └── runpod_business_model.md # RunPod pricing notes
└── index.html                   # Project landing page
```

## Key Configuration

- **RunPod endpoint ID**: `b6cpv4fbec236e` (fast, default)
- **Alternative endpoint**: `ygwnj9qla85mr8` (slow, avoid unless necessary)
- **API key**: Stored in `config/.env` as `RUNPOD_API_KEY=...`
- **Story data**: `data/story.json` — 9 chapters with `image_prompt` fields
- **Output**: `output/generated/txt2img_ch{NN}_{title}.png`

## Generation Workflow

1. Ensure `config/.env` contains `RUNPOD_API_KEY`.
2. Edit `data/story.json` to adjust prompts or story text.
3. Generate all chapters:
   ```bash
   python3 src/generators/batch.py
   ```
4. Generate a single chapter:
   ```bash
   python3 src/generators/single.py 5
   ```
5. Skip already-generated chapters:
   ```bash
   python3 src/generators/batch.py --skip-existing
   ```

## API Parameters (Default)

| Parameter | Value |
|-----------|-------|
| height / width | 1024 × 1024 |
| num_inference_steps | 40 |
| guidance_scale | 10.0 |
| strength (img2img) | 0.75 |
| scheduler | K_EULER |

## Code Conventions

- All generator scripts add `PROJECT_ROOT` to `sys.path` so `src.shared.*` imports work when run from the project root.
- Generator scripts default to **txt2img** (no seed image) so scenes render properly.
- Use `--mode seeded` with `--strength` if a portrait seed is required.
- Poll interval: 30 seconds for batch, 15 seconds for single.

## Security

- Never commit `config/.env`. It is ignored by git (see `.gitignore` if present).
- Do not paste API keys into `story.json` or other tracked files.

## Notes

- This is an ephemeral scratch workspace. Generated images and raw JSON inputs can be cleaned freely.
- The `.kilo/` directory contains workspace configuration for the Kilo IDE and should not be modified.
