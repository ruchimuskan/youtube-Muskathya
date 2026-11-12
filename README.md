# youtube-Muskathya

Autonomous AI YouTube Channel Manager — Python pipeline that generates original stories, produces video locally (Piper + FFmpeg), runs quality checks, and uploads to YouTube via OAuth—with a learning database for future improvements.

**Stack (free/local):** Cloudflare Workers AI or Ollama, Piper TTS, ComfyUI (optional), FFmpeg, SQLite, FastAPI dashboard, GitHub Actions on a **self-hosted Mac runner**.

See **`IMPLEMENTATION_STATUS.md`** for phase-by-phase completion and blockers.

## Quick start

### 1. System dependencies (macOS)

```bash
brew install ffmpeg python@3.11
# Optional: ollama, piper (or build from rhasspy/piper releases)
```

Download Piper Hindi/English ONNX models into `data/voices/` (see [Piper voices](https://github.com/rhasspy/piper/blob/master/VERSIONS.md); verify licenses).

### 2. Python environment

```bash
cd "/Users/rohitjaiswal/Desktop/youtube content"
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env — do not commit secrets
```

### 3. Database

```bash
python -m app.main init-db
```

### 4. Google / YouTube OAuth

1. Google Cloud Console → create project → enable **YouTube Data API v3** and **YouTube Analytics API**.
2. OAuth consent screen (External testing OK for your account).
3. Create OAuth client (Desktop or Web) → download JSON as `client_secrets.json` in project root.
4. Authorized redirect URI: `http://127.0.0.1:8765/oauth2/callback`

### 5. Dashboard + connect channel

```bash
python -m app.main serve
```

Open [http://127.0.0.1:8765](http://127.0.0.1:8765) → **Connect YouTube**. Complete Google sign-in yourself (the app never sees your password).

Alternatively:

```bash
python -m app.main oauth-url
```

### 6. Generate a video (local only)

```bash
# Requires Ollama running OR Cloudflare credentials in .env
python -m app.main generate
```

Output under `output/project_<id>/`.

### 7. Private test upload

```bash
# Keep PRIVACY_MODE=private in .env
python -m app.main generate --upload
```

## CLI

| Command | Description |
|---------|-------------|
| `init-db` | Create SQLite tables |
| `serve` | Dashboard + OAuth callback |
| `oauth-url` | Print authorization URL |
| `generate` | Full pipeline; add `--upload` to send to YouTube |
| `publish` | Finish SEO/thumbnail for an existing render; add `--upload` to publish |

## GitHub Actions + cron-job.org

1. Push repo to GitHub; add secrets: `CLOUDFLARE_*`, optional `AI_PROVIDER`.
2. Register self-hosted runner on your Mac with labels: `self-hosted`, `macOS`, `youtube-ai`.
3. Workflow: `.github/workflows/generate_youtube_video.yml` (`workflow_dispatch` + `repository_dispatch` event `generate_youtube_video`).
4. On [cron-job.org](https://cron-job.org), POST to GitHub API `repos/{owner}/{repo}/dispatches` with body:

```json
{
  "event_type": "generate_youtube_video",
  "client_payload": {
    "upload": false,
    "idempotency_key": "2026-11-11T10:00:00Z"
  }
}
```

Use a GitHub PAT with `repo` scope stored only in cron-job.org credentials—not in source code.

## Emergency stop

Set `EMERGENCY_STOP=true` in `.env` or GitHub Variables to block uploads and pipeline runs that check this flag.

## Tests

```bash
pytest tests/
```

## Project layout

```
app/
  ai/          # LLM, story, SEO, learning
  voice/       # Piper
  images/      # ComfyUI + fallback
  video/       # FFmpeg, QC, thumbnails
  youtube/     # OAuth, upload, analytics
  automation/  # Pipeline orchestration
  dashboard/   # FastAPI UI
  database/    # SQLAlchemy models
```

## License & content policy

Use only properly licensed voices, music, and images. Enable YouTube synthetic/altered disclosure in metadata when required. This project does not guarantee rankings, views, or monetization.
