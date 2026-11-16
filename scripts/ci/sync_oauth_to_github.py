#!/usr/bin/env python3
"""
Sync local OAuth token to GitHub Secrets automatically.
Run this after any OAuth re-authorization to keep GitHub CI in sync.

Usage:
  cd "youtube content"
  GITHUB_ADMIN_PAT=ghp_xxx .venv/bin/python scripts/ci/sync_oauth_to_github.py

Or add GITHUB_ADMIN_PAT to .env and run directly.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

# Load .env
env_file = ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"'))

try:
    import httpx
except ImportError:
    print("Run: pip install httpx")
    sys.exit(1)

try:
    from nacl import encoding, public
    import base64

    def encrypt_secret(public_key: str, secret_value: str) -> str:
        pk = public.PublicKey(public_key.encode(), encoding.Base64Encoder())
        sealed = public.SealedBox(pk).encrypt(secret_value.encode())
        return base64.b64encode(sealed).decode()
except ImportError:
    print("Run: pip install pynacl")
    sys.exit(1)

OWNER = "ruchimuskan"
REPO = "youtube-Muskathya"


def put_secret(client: httpx.Client, headers: dict, name: str, value: str) -> None:
    pk_resp = client.get(
        f"https://api.github.com/repos/{OWNER}/{REPO}/actions/secrets/public-key",
        headers=headers,
    )
    pk_resp.raise_for_status()
    key_id = pk_resp.json()["key_id"]
    key = pk_resp.json()["key"]
    enc = encrypt_secret(key, value)
    r = client.put(
        f"https://api.github.com/repos/{OWNER}/{REPO}/actions/secrets/{name}",
        headers=headers,
        json={"encrypted_value": enc, "key_id": key_id},
    )
    r.raise_for_status()
    print(f"✅ GitHub secret updated: {name}")


def main() -> int:
    admin = os.environ.get("GITHUB_ADMIN_PAT", "").strip()
    if not admin:
        print("❌ Set GITHUB_ADMIN_PAT environment variable (GitHub classic token with repo scope)")
        return 1

    oauth_path = ROOT / "data" / "oauth_tokens.json"
    client_path = ROOT / "client_secrets.json"
    if not client_path.exists():
        alt = Path.home() / "Desktop" / "youtube-google auth.json"
        if alt.exists():
            client_path = alt

    if not oauth_path.exists():
        print(f"❌ Missing OAuth token: {oauth_path}")
        return 1
    if not client_path.exists():
        print(f"❌ Missing client secrets: {client_path}")
        return 1

    headers = {
        "Authorization": f"Bearer {admin}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    with httpx.Client(timeout=30) as http:
        put_secret(http, headers, "YOUTUBE_OAUTH_TOKENS_JSON", oauth_path.read_text(encoding="utf-8"))
        put_secret(http, headers, "GOOGLE_CLIENT_SECRETS_JSON", client_path.read_text(encoding="utf-8"))

    print("\n✅ GitHub Secrets synced! CI will use the fresh OAuth token on next run.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
