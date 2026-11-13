#!/usr/bin/env bash
# Fail fast before generate/upload when local OAuth or env is missing.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi

errors=0
warn() { echo "WARN: $*"; }
die() { echo "ERROR: $*"; errors=$((errors + 1)); }

if [[ "${EMERGENCY_STOP:-false}" == "true" ]]; then
  die "EMERGENCY_STOP=true — set false in .env or GitHub Variables"
fi

if [[ ! -f "$ROOT/client_secrets.json" ]]; then
  die "Missing client_secrets.json in $ROOT"
fi

token="${YOUTUBE_OAUTH_TOKEN_FILE:-$ROOT/data/oauth_tokens.json}"
if [[ ! -f "$token" ]]; then
  die "Missing YouTube OAuth token at $token — run: python -m app.main serve → Connect YouTube"
fi

if [[ ! -d "$ROOT/.venv" ]]; then
  warn "No .venv — workflow will create one"
fi

if [[ $errors -gt 0 ]]; then
  echo ""
  echo "Preflight failed ($errors). Fix the items above; output/ and .env stay gitignored by design."
  exit 1
fi

echo "Preflight OK — $(date '+%Y-%m-%d %H:%M:%S %Z')"
