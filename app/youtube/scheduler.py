from __future__ import annotations

import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.config import get_settings

logger = logging.getLogger(__name__)


class PublishScheduler:
    """Next YouTube publish slot at configured local time (default 6:00 PM)."""

    def next_publish_time(self) -> datetime:
        settings = get_settings()
        tz = ZoneInfo(settings.timezone)
        now = datetime.now(tz)
        target = now.replace(
            hour=settings.publish_hour,
            minute=settings.publish_minute,
            second=0,
            microsecond=0,
        )
        if target <= now:
            target += timedelta(days=1)
        return target.astimezone(ZoneInfo("UTC"))
