# Fly.io Deployment Guide

## Prerequisites

- [flyctl](https://fly.io/docs/hands-on/install-flyctl/) installed
- Fly.io account (sign up at [fly.io](https://fly.io))
- RunPod API key

## Step 1 — Login to Fly.io

```bash
flyctl auth login
```

This opens a browser window to authenticate.

## Step 2 — Launch the app (first time only)

```bash
flyctl launch
```

This reads `fly.toml` and creates the app. It will ask if you want to copy the existing configuration — say **yes**.

## Step 3 — Set your RunPod API key as a secret

```bash
flyctl secrets set RUNPOD_API_KEY=rpa_YOUR_REAL_KEY_HERE
```

The API key is now stored securely on Fly.io servers and injected into the app as an environment variable. It is never exposed to the browser.

## Step 4 — Deploy

```bash
flyctl deploy
```

This builds the Docker image and deploys it.

## Step 5 — Verify

```bash
flyctl status
flyctl logs
```

Open the deployed URL (shown in `flyctl status` output).

## Architecture on Fly.io

```
Browser ──► Fly.io App (FastAPI + Docker)
                │
                ├── Serves index.html (static)
                ├── Serves story.json from /story
                ├── POST /generate ──► RunPod API (server-side API key)
                ├── GET  /status/{job_id} ──► RunPod API
                └── GET  /images/{file} ──► output/generated/*.png
                │
                └── Persistent Volume (mount: /app/output/generated)
```

## Persistent Storage

Images are saved to a Fly.io persistent volume mounted at `/app/output/generated`. This means:

- Generated images survive container restarts
- If you scale to 0 machines (auto-stop), images are still there when it starts back up
- You can download images via `flyctl ssh console` if needed

### Create the volume (first time only)

```bash
flyctl volumes create storyboard_data --region lhr --size 1
```

## Updating the Story

1. Click **Edit Story** in the web UI (links to GitHub edit page)
2. Or edit `data/story.json` locally and push to GitHub
3. Redeploy: `flyctl deploy`

## Scaling

```bash
# Scale to 1 machine always running
flyctl scale count 1

# Or let it auto-stop when idle (default)
flyctl scale count 0 --max 1
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `RUNPOD_API_KEY not configured` | Run `flyctl secrets set RUNPOD_API_KEY=...` |
| Images not persisting | Ensure volume `storyboard_data` exists and is mounted |
| Deploy fails | Check `flyctl logs` for build errors |
| CORS errors | Backend already has `allow_origins=["*"]` — check if app is reachable |

## Useful Commands

```bash
flyctl logs              # Stream app logs
flyctl ssh console       # SSH into the running container
flyctl ssh console -C "ls /app/output/generated"  # List generated images
flyctl apps destroy previz-ai-storyboard  # Tear everything down
```
