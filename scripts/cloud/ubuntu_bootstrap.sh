#!/usr/bin/env bash
# One-time on Ubuntu 22.04+ VPS (24/7). After this: cron-job.org + GitHub drive daily runs here.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

sudo apt-get update -qq
sudo apt-get install -y ffmpeg python3.11 python3.11-venv git curl

if [[ ! -d "$ROOT/.venv" ]]; then
  python3.11 -m venv "$ROOT/.venv"
fi
# shellcheck disable=SC1091
source "$ROOT/.venv/bin/activate"
pip install -q -r requirements.txt
python -m app.main init-db

echo ""
echo "Next (one time on this VPS):"
echo "  1. Copy .env, client_secrets.json, data/oauth_tokens.json from your Mac to $ROOT"
echo "  2. Install GitHub Actions runner: https://github.com/ruchimuskan/youtube-Muskathya/settings/actions/runners/new"
echo "     Labels MUST include: self-hosted, youtube-ai"
echo "  3. sudo ./svc.sh install && sudo ./svc.sh start  (inside runner folder)"
echo "  4. bash scripts/preflight_automation.sh"
echo ""
echo "Then cron-job.org + GitHub run daily with NO Mac."
