#!/usr/bin/env bash
# 6 PM IST: publish queued uploads when quota allows.
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

# shellcheck disable=SC1091
source "$ROOT/.venv/bin/activate"
python -m app.main upload-queue
