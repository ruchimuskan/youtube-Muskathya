#!/usr/bin/env python3
"""One-time: put client_secrets + oauth_tokens into GitHub Actions secrets (cloud CI)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.cronjob.push_github_secrets import put_secret  # noqa: E402

import httpx  # noqa: E402


def main() -> int:
    admin = os.environ.get("GITHUB_ADMIN_PAT", "").strip()
    if not admin:
        print("Set GITHUB_ADMIN_PAT")
        return 1

    client = ROOT / "client_secrets.json"
    oauth = ROOT / "data" / "oauth_tokens.json"
    if not client.exists():
        alt = Path.home() / "Desktop" / "youtube-google auth.json"
        if alt.exists():
            client.write_bytes(alt.read_bytes())
    for p in (client, oauth):
        if not p.exists():
            print(f"Missing {p}")
            return 1

    headers = {
        "Authorization": f"Bearer {admin}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    with httpx.Client(timeout=60) as http:
        put_secret(http, headers, "GOOGLE_CLIENT_SECRETS_JSON", client.read_text(encoding="utf-8"))
        put_secret(http, headers, "YOUTUBE_OAUTH_TOKENS_JSON", oauth.read_text(encoding="utf-8"))
    print("GitHub secrets set: GOOGLE_CLIENT_SECRETS_JSON, YOUTUBE_OAUTH_TOKENS_JSON")
    return 0


if __name__ == "__main__":
    sys.exit(main())
