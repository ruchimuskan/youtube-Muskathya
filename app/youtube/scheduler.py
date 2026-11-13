from __future__ import annotations

import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.config import get_settings

logger = logging.getLogger(__name__)


class PublishScheduler:
    """Next YouTube publish slot at configured local time (default 6:00 PM)."""

    def _slot(self, day_offset: int = 0) -> datetime:
        settings = get_settings()
        tz = ZoneInfo(settings.timezone)
        now = datetime.now(tz)
        target = now.replace(
            hour=settings.publish_hour,
            minute=settings.publish_minute,
            second=0,
            microsecond=0,
        ) + timedelta(days=day_offset)
        return target

    def next_publish_time(self) -> datetime:
        """Next 6 PM slot in channel timezone (today if still upcoming, else tomorrow)."""
        tz = ZoneInfo(get_settings().timezone)
        now = datetime.now(tz)
        target = self._slot(0)
        if target <= now:
            target = self._slot(1)
        return target.astimezone(ZoneInfo("UTC"))

    def next_slot_when_quota_exhausted(self) -> datetime:
        """Earliest 6 PM slot when today's upload quota is already used (always tomorrow 6 PM)."""
        from app.database import Repository, session_scope

        settings = get_settings()
        with session_scope() as session:
            full = Repository(session).uploads_today_count() >= settings.max_daily_uploads

        tz = ZoneInfo(settings.timezone)
        now = datetime.now(tz)
        today_slot = self._slot(0)

        if full or today_slot <= now:
            return self._slot(1).astimezone(ZoneInfo("UTC"))
        return today_slot.astimezone(ZoneInfo("UTC"))
