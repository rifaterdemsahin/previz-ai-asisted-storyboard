# AI-Assisted Storyboard Generator

> **Live Demo:** [https://rifaterdemsahin.github.io/previz-ai-asisted-storyboard/](https://rifaterdemsahin.github.io/previz-ai-asisted-storyboard/)

---

## How It Works

1. **Write your story** in `data/story.json` — one chapter per entry with a descriptive `image_prompt`.
2. **Run the batch generator** — `batch.py` sends each prompt to RunPod Serverless SDXL.
3. **Poll for results** — images are saved as PNGs in `output/generated/`.
4. **View the storyboard** — open `index.html` in any browser. It has two views:
   - **Carousel** — browse one chapter at a time with prev/next buttons and dot navigation.
   - **Storyboard** — grid of all chapters with thumbnails. Click any card for a full-screen modal.

---

## Quick Start (5 Minutes)

### 1. Clone and enter the project

```bash
git clone https://github.com/rifaterdemsahin/previz-ai-asisted-storyboard.git
cd previz-ai-asisted-storyboard
```

### 2. Configure your RunPod API key

```bash
cp config/sample_env config/.env
# Edit config/.env and replace the placeholder with your real key
```

See the [RunPod setup guide below](#runpod-setup-guide) if you don't have a key yet.

### 3. Generate the story images

```bash
python3 src/generators/batch.py
```

This runs all 9 chapters. Each takes ~20–40 seconds. Images appear in `output/generated/`.

### 4. View the storyboard

```bash
open index.html        # macOS
xdg-open index.html    # Linux
start index.html       # Windows
```

Or open it directly in your browser. No build step required — it's vanilla HTML/CSS/JS.

---

## Creating Your Own Storyboard

### Step 1 — Edit `data/story.json`

The file has three top-level keys:

| Key | Purpose |
|-----|---------|
| `title` | Story title (shown in the page header) |
| `seed_image_url` | Optional portrait seed for img2img consistency |
| `chapters` | Array of chapter objects |

Each chapter needs:

```json
{
  "chapter": 1,
  "title": "The Discovery",
  "setting": "Berlin coffee shop, afternoon",
  "text": "Alex had been stuck on the same bug for three hours...",
  "image_prompt": "A young developer sitting in a cozy Berlin coffee shop..."
}
```

**Tips for great prompts:**
- Start with the **scene** (where, when, mood) and end with **character tags**.
- Use cinematic keywords: *cinematic lighting, highly detailed, 8k, golden hour*.
- Mention specific environments so the model renders backgrounds, not just portraits.
- Keep each prompt under ~80 words — SDXL pays most attention to the first tokens.

### Step 2 — Match filenames in `index.html`

The viewer expects images named like `txt2img_ch01_the_discovery.png`. If you change titles, update the `chapters` array in `index.html` so `file` matches the actual output name.

### Step 3 — Generate

```bash
# All chapters
python3 src/generators/batch.py

# One chapter only (e.g., Chapter 3)
python3 src/generators/single.py 3

# With a portrait seed for character consistency
python3 src/generators/batch.py --mode seeded --strength 0.65
```

### Step 4 — Refresh the browser

The HTML auto-detects whether an image exists (on `img.onload`). If a chapter hasn't been generated yet, it shows a **"Generate"** badge and a placeholder.

---

## Project Structure

```
├── config/
│   ├── .env              ← Live credentials (ignored by git)
│   └── sample_env        ← Template with placeholders
├── data/
│   └── story.json        ← Your story + image prompts
├── src/
│   ├── shared/
│   │   ├── env.py        ← .env loader (no external deps)
│   │   └── runpod_client.py  ← API client + image extraction
│   ├── generators/
│   │   ├── batch.py      ← Generate all chapters
│   │   ├── single.py     ← Generate one chapter
│   │   └── chapter_one.py← Quick Chapter 1 test
│   └── utils/
│       ├── base64_to_image.py   ← Decode RunPod JSON to PNG
│       ├── image_to_base64.py   ← Encode a seed image
│       └── url_converter.py     ← Fix Google Drive/Dropbox URLs
├── scripts/
│   └── runpod_query.py   ← Quick API connectivity test
├── output/
│   └── generated/        ← PNG outputs land here
├── input/
│   └── raw/              ← Raw RunPod JSON responses
├── docs/
│   ├── environment.md    ← Detailed RunPod setup
│   ├── HOWTO.md          ← CLI usage guide
│   └── AGENTS.md         ← Dev conventions
└── index.html            ← Carousel + Storyboard viewer
```

---

## RunPod Setup Guide

### What is RunPod?

[RunPod](https://www.runpod.io) is a cloud GPU rental platform. Its **Serverless** product lets you run Stable Diffusion XL on-demand without managing a server. You pay only for the seconds the GPU is active (~$0.003 per 1024×1024 image).

### Step 1 — Create an account

1. Go to [runpod.io](https://www.runpod.io) and sign up.
2. Add a payment method (credit card or crypto).

### Step 2 — Get your API key

1. In the RunPod console, go to **Settings**.
2. Under **API Keys**, click **Create API Key**.
3. Copy the key (it starts with `rpa_`).

### Step 3 — Create a Serverless endpoint

1. Navigate to **Serverless** in the sidebar.
2. Click **New Endpoint**.
3. Choose a template:
   - **SDXL** — best general quality.
   - **SDXL + Refiner** — sharper details (slower).
4. Select a GPU:
   - **RTX 4090** — fast and cheap (recommended).
   - **A100** — overkill for 1024×1024 images.
5. Set **Max Workers** to at least `1`.
6. Click **Deploy**.
7. Copy the **Endpoint ID** (looks like `b6cpv4fbec236e`).

### Step 4 — Add credentials to the project

```bash
cp config/sample_env config/.env
```

Edit `config/.env`:

```bash
RUNPOD_API_KEY=rpa_YOUR_REAL_KEY_HERE
RUNPOD_ENDPOINT_ID=your_endpoint_id_here
```

> **Security:** `config/.env` is in `.gitignore`. Never commit it.

### Step 5 — Verify connectivity

```bash
python3 scripts/runpod_query.py
```

Expected output:

```
Sending request to RunPod endpoint b6cpv4fbec236e...
{
  "id": "job-id-here",
  "status": "IN_QUEUE"
}
Saved response to: input/raw/runpod_job-id-here.json
```

If you see `Error 401`, your API key is invalid. If it hangs in `IN_QUEUE` for more than 5 minutes, the endpoint is cold-starting or overloaded.

### Pricing Notes

| Action | Typical Cost |
|--------|-------------|
| Cold start (first request after idle) | ~10–20 seconds of GPU time |
| 1024×1024 image, 40 inference steps | ~$0.003–$0.005 |
| Full 9-chapter batch | ~$0.03–$0.05 |
| Monthly 100-image batch | ~$0.50–$1.00 |

*Prices vary by GPU type and RunPod's current rates. Always check your [billing dashboard](https://www.runpod.io/console/billing).*

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `RUNPOD_API_KEY not found` | Ensure `config/.env` exists and has the key. |
| `IN_QUEUE` forever | Endpoint is cold or busy. Wait, or increase **Max Workers** in RunPod. |
| `Error 401` | Invalid API key. Regenerate it in RunPod Settings. |
| Images are just portraits, no scene | Use `txt2img` mode (default) instead of `seeded`, or lower portrait description weight in prompts. |
| `No image data found` | Check `input/raw/*.json` for error messages from RunPod. |
| `index.html` shows "Not yet generated" badges | Run `python3 src/generators/batch.py` first. |

---

## License

MIT — use it to visualize your own stories, presentations, or comic panels.

---

**Built with** RunPod Serverless · Stable Diffusion XL · Python 3 · vanilla JS
