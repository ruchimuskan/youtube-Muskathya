from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)


class TTSLogger:
    def __init__(self, work_dir: Path | None = None) -> None:
        settings = get_settings()
        self.work_dir = work_dir
        self.global_log = settings.log_dir / "tts_pipeline.jsonl"
        self.global_log.parent.mkdir(parents=True, exist_ok=True)

    def log_segment(self, record: dict[str, Any]) -> None:
        record["ts"] = datetime.now(timezone.utc).isoformat()
        line = json.dumps(record, ensure_ascii=False)
        with self.global_log.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
        if self.work_dir:
            per_job = self.work_dir / "tts_segments.jsonl"
            with per_job.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        logger.info(
            "TTS segment sn=%s seg=%s dur=%.2fs ok=%s",
            record.get("scene_number"),
            record.get("segment_id"),
            record.get("duration_sec", 0),
            record.get("verify_passed"),
        )
