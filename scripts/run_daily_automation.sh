#!/usr/bin/env bash
# 3 PM IST: generate + upload (or queue). Safe for cron / launchd.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi

"$ROOT/scripts/preflight_automation.sh"

if [[ ! -d "$ROOT/.venv" ]]; then
  python3.11 -m venv "$ROOT/.venv"
  # shellcheck disable=SC1091
  source "$ROOT/.venv/bin/activate"
  pip install -q -r requirements.txt
else
  # shellcheck disable=SC1091
  source "$ROOT/.venv/bin/activate"
fi

python -m app.main init-db

# Process any deferred uploads from yesterday first
python -m app.main upload-queue || true

KEY="daily-$(TZ="${TIMEZONE:-Asia/Kolkata}" date +%Y-%m-%d)"
python -m app.main generate --upload --idempotency-key "$KEY"
