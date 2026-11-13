#!/usr/bin/env bash
# Write OAuth files from GitHub Actions secrets (no Mac).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
mkdir -p data

if [[ -n "${GOOGLE_CLIENT_SECRETS_JSON:-}" ]]; then
  printf '%s' "$GOOGLE_CLIENT_SECRETS_JSON" > "$ROOT/client_secrets.json"
elif [[ -n "${GOOGLE_CLIENT_SECRETS_B64:-}" ]]; then
  echo "$GOOGLE_CLIENT_SECRETS_B64" | base64 -d > "$ROOT/client_secrets.json"
fi

if [[ -n "${YOUTUBE_OAUTH_TOKENS_JSON:-}" ]]; then
  printf '%s' "$YOUTUBE_OAUTH_TOKENS_JSON" > "$ROOT/data/oauth_tokens.json"
elif [[ -n "${YOUTUBE_OAUTH_TOKENS_B64:-}" ]]; then
  echo "$YOUTUBE_OAUTH_TOKENS_B64" | base64 -d > "$ROOT/data/oauth_tokens.json"
fi

chmod 600 "$ROOT/client_secrets.json" 2>/dev/null || true
chmod 600 "$ROOT/data/oauth_tokens.json" 2>/dev/null || true

test -f "$ROOT/client_secrets.json" && test -f "$ROOT/data/oauth_tokens.json"
