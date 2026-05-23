# Environment Setup Guide — RunPod Image Generation

## Overview

This project generates story chapter images using **RunPod Serverless** with Stable Diffusion XL. This guide explains how to set up your local environment and configure the RunPod backend.

## Prerequisites

- Python 3.10+
- A RunPod account (free tier available)
- A RunPod API key

## Step 1 — Get Your RunPod API Key

1. Sign up at [runpod.io](https://www.runpod.io).
2. Go to **Console → Settings**.
3. Copy your API key under **API Keys**.
4. Paste it into `config/.env`:

   ```bash
   cp config/sample_env config/.env
   # Edit config/.env and replace your_runpod_api_key_here with the real key
   ```

## Step 2 — Create a Serverless Endpoint

1. In the RunPod console, go to **Serverless**.
2. Click **New Endpoint**.
3. Select a Stable Diffusion XL template (e.g., "SDXL" or "SDXL with Refiner").
4. Choose your GPU type (RTX 4090 is fast; A100 is overkill for 1024×1024).
5. Set **Max Workers** to at least 1.
6. Copy the **Endpoint ID** (looks like `b6cpv4fbec236e`).
7. Add it to `config/.env`:

   ```bash
   RUNPOD_ENDPOINT_ID=your_endpoint_id_here
   ```

   If you omit this, scripts default to `b6cpv4fbec236e`.

## Step 3 — Verify Connectivity

Run the test script:

```bash
python3 scripts/runpod_query.py
```

Expected output:

```
Sending request to RunPod endpoint b6cpv4fbec236e...
{
  "id": "...",
  "status": "IN_QUEUE"
}
Saved response to: input/raw/runpod_....json
```

If you see an authentication error, double-check your API key.

## Step 4 — Generate Your First Image

```bash
python3 src/generators/chapter_one.py
```

This generates Chapter 1 and saves it to:

```
output/generated/story_ch01_the_discovery.png
```

## RunPod Pricing Notes

| Action | Cost |
|--------|------|
| Cold start (first request after idle) | ~10–20 s |
| 1024×1024 image, 40 steps | ~$0.003–$0.005 |
| 9-chapter batch | ~$0.03–$0.05 |

*Prices vary by GPU type and current RunPod rates.*

## Security Checklist

- [ ] `config/.env` is listed in `.gitignore` and never committed.
- [ ] `config/sample_env` contains only placeholders.
- [ ] API keys are rotated if accidentally exposed.
- [ ] Endpoint is kept in **Private** mode unless you explicitly need public access.

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `RUNPOD_API_KEY not found` | Missing or misnamed `.env` | Ensure `config/.env` exists and has the key. |
| `IN_QUEUE` for > 5 min | Endpoint cold start or queue | Wait, or increase max workers in RunPod console. |
| `Error 401` | Invalid API key | Regenerate key in RunPod settings. |
| `No image data found` | Endpoint returned non-image output | Check `input/raw/*.json` for error messages. |
| Out of memory | Batch too large or resolution too high | Reduce `num_inference_steps` or use a smaller resolution. |

## Related Files

- `config/sample_env` — Placeholder template.
- `config/.env` — Your live credentials (ignored by git).
- `src/shared/runpod_client.py` — Shared API client code.
- `docs/HOWTO.md` — CLI usage for generators.
