from __future__ import annotations

import logging
from typing import Any

from app.database import Repository, session_scope
from app.database.models import JobStatus

logger = logging.getLogger(__name__)


class JobManager:
    def start(self, job_type: str, idempotency_key: str | None = None) -> int | None:
        with session_scope() as session:
            job = Repository(session).acquire_job(job_type, idempotency_key)
            if job is None:
                logger.info("Skipping duplicate job: %s", idempotency_key)
                return None
            return job.id

    def finish(self, job_id: int, success: bool, error: str | None = None) -> None:
        with session_scope() as session:
            from app.database.models import AutomationJob

            job = session.get(AutomationJob, job_id)
            if job:
                Repository(session).finish_job(job, success, error)

    def pending_recovery_note(self) -> dict[str, Any]:
        """Document offline-runner behavior (no duplicate execution)."""
        return {
            "message": "If runner offline, cron dispatch should retry; idempotency_key prevents duplicates.",
        }
