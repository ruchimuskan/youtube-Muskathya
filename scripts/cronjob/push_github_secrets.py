#!/usr/bin/env python3
"""One-time: set CRONJOB_API_KEY and GH_DISPATCH_PAT on GitHub (needs admin PAT).

Usage:
  export GITHUB_ADMIN_PAT=ghp_...   # your GitHub token (classic, repo + admin:repo_hook or repo full)
  export CRONJOB_API_KEY=...
  export GH_DISPATCH_PAT=ghp_...    # can be same token as GITHUB_ADMIN_PAT
  python scripts/cronjob/push_github_secrets.py
"""
from __future__ import annotations

import base64
import os
import sys

import httpx

try:
    from nacl import encoding, public
except ImportError:
    print("pip install pynacl")
    sys.exit(1)

OWNER = "ruchimuskan"
REPO = "youtube-Muskathya"


def encrypt_secret(public_key: str, secret_value: str) -> str:
    pk = public.PublicKey(public_key.encode(), encoding.Base64Encoder())
    sealed = public.SealedBox(pk).encrypt(secret_value.encode())
    return base64.b64encode(sealed).decode()


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
    print(f"GitHub secret set: {name}")


def main() -> int:
    admin = os.environ.get("GITHUB_ADMIN_PAT", "").strip()
    cron_key = os.environ.get("CRONJOB_API_KEY", "").strip()
    dispatch = os.environ.get("GH_DISPATCH_PAT", "").strip()
    if not admin:
        print("Set GITHUB_ADMIN_PAT (token that can manage repo secrets)")
        return 1
    if not cron_key:
        print("Set CRONJOB_API_KEY")
        return 1
    if not dispatch:
        dispatch = admin

    headers = {
        "Authorization": f"Bearer {admin}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    cf_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip()
    cf_tok = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()

    with httpx.Client(timeout=60) as client:
        put_secret(client, headers, "CRONJOB_API_KEY", cron_key)
        put_secret(client, headers, "GH_DISPATCH_PAT", dispatch)
        if cf_id:
            put_secret(client, headers, "CLOUDFLARE_ACCOUNT_ID", cf_id)
        if cf_tok:
            put_secret(client, headers, "CLOUDFLARE_API_TOKEN", cf_tok)
    return 0


if __name__ == "__main__":
    sys.exit(main())
