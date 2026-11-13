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

SECRETS="${GOOGLE_CLIENT_SECRETS_FILE:-$ROOT/client_secrets.json}"
if [[ ! -f "$SECRETS" ]]; then
  if [[ -n "${GITHUB_ACTIONS:-}" ]]; then
    die "Missing client_secrets.json on CI — set GitHub secret GOOGLE_CLIENT_SECRETS_JSON"
  fi
  ALT="$HOME/Desktop/youtube-google auth.json"
  if [[ -f "$ALT" ]]; then
    cp "$ALT" "$ROOT/client_secrets.json"
    SECRETS="$ROOT/client_secrets.json"
    echo "INFO: Copied OAuth client JSON from Desktop → client_secrets.json"
  else
    die "Missing client_secrets.json (download from Google Cloud or set GOOGLE_CLIENT_SECRETS_FILE)"
  fi
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
