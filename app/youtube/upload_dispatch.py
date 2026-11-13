from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.utils.workspace_paths import abs_path
from app.youtube.scheduler import PublishScheduler
from app.youtube.upload_queue import can_upload_today, enqueue
from app.youtube.uploader import YouTubeUploader

logger = logging.getLogger(__name__)


def dispatch_youtube_upload(
    *,
    video_asset_id: int,
    video_path: Path,
    thumbnail_path: Path | None,
    metadata: dict[str, Any],
    story_id: int | None = None,
) -> dict[str, Any]:
    """
    Upload now if daily quota allows; otherwise queue for the next 6 PM IST slot.
    When schedule mode is on and quota is free, sets YouTube publishAt to next 6 PM.
    """
    settings = get_settings()

    if not can_upload_today():
        slot = PublishScheduler().next_slot_when_quota_exhausted()
        entry = enqueue(
            video_asset_id=video_asset_id,
            video_path=str(abs_path(video_path)),
            thumbnail_path=str(abs_path(thumbnail_path)) if thumbnail_path else None,
            metadata=metadata,
            story_id=story_id,
            publish_at_utc=slot,
            reason="daily_quota",
        )
        return {
            "status": "queued",
            "publish_at": entry["publish_at"],
            "queue_id": entry["id"],
        }

    privacy = settings.privacy_mode
    publish_at: datetime | None = None
    if settings.publishing_mode == "schedule":
        publish_at = PublishScheduler().next_publish_time()
        if privacy == "private":
            privacy = "public"

    uploader = YouTubeUploader()
    upload_info = uploader.upload_video(
        video_asset_id,
        abs_path(video_path),
        metadata,
        privacy=privacy,
        publish_at=publish_at,
        thumbnail_path=thumbnail_path,
    )
    return {
        "status": "uploaded",
        "publish_at": publish_at.isoformat() if publish_at else None,
        **upload_info,
    }
