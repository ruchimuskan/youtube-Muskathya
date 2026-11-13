from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.database.models import (
    AIUsageLog,
    AuditLog,
    AutomationJob,
    ChannelConnection,
    JobStatus,
    LearningRecord,
    StoryProject,
    VideoAsset,
    YouTubeUpload,
)


class Repository:
    def __init__(self, session: Session):
        self.session = session

    def init_db(self) -> None:
        from app.database.base import Base
        from app.database.session import get_engine

        Base.metadata.create_all(get_engine())

    # Channel
    def save_channel(self, channel_id: str, channel_title: str) -> ChannelConnection:
        existing = self.session.scalar(
            select(ChannelConnection).where(ChannelConnection.channel_id == channel_id)
        )
        if existing:
            existing.channel_title = channel_title
            existing.is_active = True
            return existing
        row = ChannelConnection(channel_id=channel_id, channel_title=channel_title)
        self.session.add(row)
        self.session.flush()
        return row

    def get_active_channel(self) -> ChannelConnection | None:
        return self.session.scalar(
            select(ChannelConnection).where(ChannelConnection.is_active.is_(True)).limit(1)
        )

    # Stories & videos
    def create_story(self, **kwargs: Any) -> StoryProject:
        row = StoryProject(**kwargs)
        self.session.add(row)
        self.session.flush()
        return row

    def create_video_asset(self, **kwargs: Any) -> VideoAsset:
        row = VideoAsset(**kwargs)
        self.session.add(row)
        self.session.flush()
        return row

    def get_video(self, video_id: int) -> VideoAsset | None:
        return self.session.get(VideoAsset, video_id)

    # Learning
    def get_recent_lessons(self, limit: int = 20) -> list[LearningRecord]:
        stmt = select(LearningRecord).order_by(desc(LearningRecord.created_at)).limit(limit)
        return list(self.session.scalars(stmt))

    def add_lesson(self, category: str, lesson: str, evidence: dict[str, Any] | None = None) -> LearningRecord:
        row = LearningRecord(category=category, lesson=lesson, evidence=evidence)
        self.session.add(row)
        self.session.flush()
        return row

    def audit(self, action: str, entity_type: str, entity_id: str | None = None, details: dict | None = None):
        self.session.add(
            AuditLog(action=action, entity_type=entity_type, entity_id=entity_id, details=details)
        )

    # AI usage
    def log_ai_usage(self, provider: str, model: str, tokens: int, success: bool) -> None:
        self.session.add(
            AIUsageLog(provider=provider, model=model, tokens_estimated=tokens, success=success)
        )

    def cloudflare_usage_today(self) -> int:
        today = datetime.now(timezone.utc).date()
        rows = self.session.scalars(
            select(AIUsageLog).where(
                AIUsageLog.provider == "cloudflare",
                AIUsageLog.success.is_(True),
            )
        )
        return sum(1 for r in rows if r.created_at.date() == today)

    # Jobs
    def acquire_job(self, job_type: str, idempotency_key: str | None) -> AutomationJob | None:
        if idempotency_key:
            existing = self.session.scalar(
                select(AutomationJob).where(AutomationJob.idempotency_key == idempotency_key)
            )
            if existing:
                return None
        job = AutomationJob(
            job_type=job_type,
            status=JobStatus.running,
            idempotency_key=idempotency_key,
            started_at=datetime.now(timezone.utc),
        )
        self.session.add(job)
        self.session.flush()
        return job

    def finish_job(self, job: AutomationJob, success: bool, error: str | None = None) -> None:
        job.status = JobStatus.completed if success else JobStatus.failed
        job.error_message = error
        job.finished_at = datetime.now(timezone.utc)

    def uploads_today_count(self) -> int:
        from zoneinfo import ZoneInfo

        from app.config import get_settings

        tz = ZoneInfo(get_settings().timezone)
        today = datetime.now(tz).date()
        rows = self.session.scalars(select(YouTubeUpload))
        return sum(
            1
            for u in rows
            if u.uploaded_at
            and u.uploaded_at.replace(tzinfo=timezone.utc).astimezone(tz).date() == today
        )
