from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from app.automation.pipeline import ContentPipeline
from app.config import get_settings
from app.youtube.upload_queue import process_due

logger = logging.getLogger(__name__)


def _run_publish_queue() -> None:
    settings = get_settings()
    if settings.emergency_stop:
        return
    logger.info("Processing deferred YouTube upload queue")
    done = process_due()
    if done:
        logger.info("Published %s queued video(s)", len(done))


def _run_daily_job() -> None:
    settings = get_settings()
    if settings.emergency_stop:
        logger.warning("Emergency stop enabled — skipping daily job")
        return
    _run_publish_queue()
    now = datetime.now(ZoneInfo(settings.timezone))
    idem = f"daily-{now.strftime('%Y-%m-%dT%H:%M')}"
    logger.info("Starting daily video job (idempotency=%s)", idem)
    ContentPipeline().run(upload=True, idempotency_key=idem)


def start_blocking_scheduler() -> None:
    """Run video generation daily (default 3 PM IST) and schedule YouTube publish at 6 PM."""
    settings = get_settings()
    sched = BlockingScheduler(timezone=settings.timezone)
    sched.add_job(
        _run_daily_job,
        CronTrigger(
            hour=settings.pipeline_daily_run_hour,
            minute=settings.pipeline_daily_run_minute,
        ),
        id="daily_youtube_video",
        replace_existing=True,
    )
    sched.add_job(
        _run_publish_queue,
        CronTrigger(
            hour=settings.publish_hour,
            minute=settings.publish_minute,
        ),
        id="youtube_upload_queue",
        replace_existing=True,
    )
    logger.info(
        "Daily scheduler started: generate at %02d:%02d %s → publish ~%02d:%02d",
        settings.pipeline_daily_run_hour,
        settings.pipeline_daily_run_minute,
        settings.timezone,
        settings.publish_hour,
        settings.publish_minute,
    )
    sched.start()


run_blocking_scheduler = start_blocking_scheduler
