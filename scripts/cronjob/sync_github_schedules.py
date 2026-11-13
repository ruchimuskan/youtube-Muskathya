#!/usr/bin/env python3
"""Register or update cron-job.org jobs that trigger GitHub repository_dispatch.

Requires env:
  CRONJOB_API_KEY — from https://console.cron-job.org → Settings
  GH_DISPATCH_PAT — GitHub PAT (classic) with `repo` scope for dispatch API

Optional:
  GITHUB_REPOSITORY — owner/repo (default from git or ruchimuskan/youtube-Muskathya)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from typing import Any

import httpx

CRON_API = "https://api.cron-job.org"
POST_METHOD = 1

DEFAULT_REPO = "ruchimuskan/youtube-Muskathya"


def _repo_slug() -> str:
    env = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if env:
        return env
    try:
        out = subprocess.check_output(
            ["git", "config", "--get", "remote.origin.url"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        if "github.com:" in out:
            return out.split("github.com:")[-1].replace(".git", "")
        if "github.com/" in out:
            return out.split("github.com/")[-1].replace(".git", "")
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return DEFAULT_REPO


def _dispatch_jobs(repo: str, pat: str) -> list[dict[str, Any]]:
    url = f"https://api.github.com/repos/{repo}/dispatches"
    body_template = lambda event_type: json.dumps(
        {"event_type": event_type, "client_payload": {"source": "cron-job.org"}}
    )
    headers = {
        "Authorization": f"Bearer {pat}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
    }
    return [
        {
            "title": "Muskathya — 3PM IST video + YouTube upload",
            "url": url,
            "event_type": "daily_pipeline",
            "schedule": {
                "timezone": "Asia/Kolkata",
                "expiresAt": 0,
                "hours": [15],
                "minutes": [0],
                "mdays": [-1],
                "months": [-1],
                "wdays": [-1],
            },
            "extendedData": {
                "headers": headers,
                "body": body_template("daily_pipeline"),
            },
        },
        {
            "title": "Muskathya — 6PM IST deferred upload queue",
            "url": url,
            "event_type": "upload_queue",
            "schedule": {
                "timezone": "Asia/Kolkata",
                "expiresAt": 0,
                "hours": [18],
                "minutes": [0],
                "mdays": [-1],
                "months": [-1],
                "wdays": [-1],
            },
            "extendedData": {
                "headers": headers,
                "body": body_template("upload_queue"),
            },
        },
    ]


def _cron_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def list_jobs(client: httpx.Client, api_key: str) -> list[dict[str, Any]]:
    r = client.get(f"{CRON_API}/jobs", headers=_cron_headers(api_key), timeout=30)
    r.raise_for_status()
    return r.json().get("jobs") or []


def upsert_job(client: httpx.Client, api_key: str, spec: dict[str, Any], existing_id: int | None) -> int:
    job = {
        "enabled": True,
        "title": spec["title"],
        "saveResponses": True,
        "url": spec["url"],
        "requestMethod": POST_METHOD,
        "requestTimeout": 300,
        "schedule": spec["schedule"],
        "extendedData": spec["extendedData"],
    }
    time.sleep(1.1)  # cron-job.org create rate limit
    if existing_id is None:
        r = client.put(f"{CRON_API}/jobs", headers=_cron_headers(api_key), json={"job": job}, timeout=30)
        r.raise_for_status()
        job_id = int(r.json()["jobId"])
        print(f"Created cron job {job_id}: {spec['title']}")
        return job_id
    r = client.patch(
        f"{CRON_API}/jobs/{existing_id}",
        headers=_cron_headers(api_key),
        json={"job": job},
        timeout=30,
    )
    r.raise_for_status()
    print(f"Updated cron job {existing_id}: {spec['title']}")
    return existing_id


def main() -> int:
    api_key = os.environ.get("CRONJOB_API_KEY", "").strip()
    pat = os.environ.get("GH_DISPATCH_PAT", "").strip()
    if not api_key:
        print("Skip: CRONJOB_API_KEY not set (add GitHub secret to auto-sync cron-job.org)")
        return 0
    if not pat:
        print("ERROR: GH_DISPATCH_PAT required — GitHub PAT with repo scope for repository_dispatch")
        return 1

    repo = _repo_slug()
    specs = _dispatch_jobs(repo, pat)
    print(f"Syncing cron-job.org → {repo}")

    with httpx.Client() as client:
        existing = {j.get("title"): j.get("jobId") for j in list_jobs(client, api_key)}
        for spec in specs:
            jid = existing.get(spec["title"])
            upsert_job(client, api_key, spec, jid)

    print("Done — schedules active on https://console.cron-job.org/dashboard")
    return 0


if __name__ == "__main__":
    sys.exit(main())
