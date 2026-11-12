from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)


class ContentCalendar:
    """File-backed calendar until dedicated DB UI grows."""

    def __init__(self) -> None:
        settings = get_settings()
        self.path = settings.data_dir / "content_calendar.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text(json.dumps({"entries": []}, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load(self) -> dict[str, Any]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, data: dict[str, Any]) -> None:
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def plan_entry(self, *, category_id: str, topic: str, format_mode: str, status: str = "planned") -> dict:
        data = self._load()
        entry = {
            "id": len(data["entries"]) + 1,
            "category_id": category_id,
            "topic": topic,
            "format_mode": format_mode,
            "status": status,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        data["entries"].append(entry)
        self._save(data)
        return entry

    def mark_status(self, story_id: int, status: str, **extra: Any) -> None:
        data = self._load()
        for e in reversed(data["entries"]):
            if e.get("story_id") == story_id:
                e["status"] = status
                e.update(extra)
                break
        else:
            data["entries"].append(
                {
                    "id": len(data["entries"]) + 1,
                    "story_id": story_id,
                    "status": status,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    **extra,
                }
            )
        self._save(data)

    def upcoming(self, limit: int = 10) -> list[dict]:
        data = self._load()
        planned = [e for e in data["entries"] if e.get("status") in ("planned", "generating", "generated", "approved")]
        return planned[-limit:]
