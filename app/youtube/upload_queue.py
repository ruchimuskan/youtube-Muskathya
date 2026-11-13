from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from app.config import get_settings
from app.database import Repository, session_scope
from app.utils.workspace_paths import abs_path, abs_path_str
from app.youtube.scheduler import PublishScheduler
from app.youtube.uploader import YouTubeUploader

logger = logging.getLogger(__name__)

QUEUE_PATH = Path("./data/pending_youtube_uploads.json")


def _load() -> list[dict[str, Any]]:
    if not QUEUE_PATH.exists():
        return []
    try:
        return json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logger.warning("Corrupt upload queue file; resetting")
        return []


def _save(items: list[dict[str, Any]]) -> None:
    QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    QUEUE_PATH.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def can_upload_today() -> bool:
    settings = get_settings()
    with session_scope() as session:
        count = Repository(session).uploads_today_count()
    return count < settings.max_daily_uploads


def enqueue(
    *,
    video_asset_id: int,
    video_path: str,
    thumbnail_path: str | None,
    metadata: dict[str, Any],
    story_id: int | None = None,
    publish_at_utc: datetime | None = None,
    reason: str = "daily_quota",
) -> dict[str, Any]:
    if publish_at_utc is None:
        publish_at_utc = PublishScheduler().next_slot_when_quota_exhausted()

    video_path = abs_path_str(video_path)
    thumbnail_path = abs_path_str(thumbnail_path) if thumbnail_path else None

    entry = {
        "id": f"story_{story_id or 0}_{int(datetime.now().timestamp())}",
        "video_asset_id": video_asset_id,
        "story_id": story_id,
        "video_path": video_path,
        "thumbnail_path": thumbnail_path,
        "metadata": metadata,
        "publish_at": publish_at_utc.isoformat(),
        "queued_at": datetime.now(ZoneInfo("UTC")).isoformat(),
        "reason": reason,
    }
    items = _load()
    items.append(entry)
    _save(items)
    logger.info(
        "Queued YouTube upload asset=%s publish_at=%s reason=%s",
        video_asset_id,
        entry["publish_at"],
        reason,
    )
    return entry


def process_due(*, force: bool = False) -> list[dict[str, Any]]:
    """Upload queued videos when quota allows and publish time has arrived."""
    settings = get_settings()
    tz = ZoneInfo(settings.timezone)
    now = datetime.now(tz)
    items = _load()
    if not items:
        return []

    if not can_upload_today():
        logger.info("Upload queue: daily quota full — will retry on next run")
        return []

    uploader = YouTubeUploader()
    done: list[dict[str, Any]] = []
    remaining: list[dict[str, Any]] = []

    for idx, item in enumerate(items):
        if not can_upload_today():
            remaining.extend(items[idx:])
            break

        pub_raw = item.get("publish_at")
        if pub_raw and not force:
            pub = datetime.fromisoformat(pub_raw.replace("Z", "+00:00")).astimezone(tz)
            if pub > now:
                remaining.append(item)
                continue

        video_path = abs_path(item["video_path"])
        if not video_path.exists():
            logger.error("Queued upload missing file: %s (keeping in queue)", video_path)
            item["last_error"] = f"missing_file:{video_path}"
            remaining.append(item)
            continue

        thumb = Path(item["thumbnail_path"]) if item.get("thumbnail_path") else None
        privacy = "public" if settings.publishing_mode == "schedule" else settings.privacy_mode
        # Queue ran at or after the planned 6 PM slot → go public immediately.
        publish_at = None

        try:
            result = uploader.upload_video(
                item["video_asset_id"],
                video_path,
                item["metadata"],
                privacy=privacy,
                publish_at=publish_at,
                thumbnail_path=thumb,
            )
            item["result"] = result
            done.append(item)
            logger.info("Queued upload completed: %s", result.get("youtube_url"))
        except Exception as exc:
            logger.exception("Queued upload failed: %s", exc)
            item["last_error"] = str(exc)
            remaining.append(item)
            break

    _save(remaining)
    return done
