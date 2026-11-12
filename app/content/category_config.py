from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.content.categories import CATEGORIES, get_category

logger = logging.getLogger(__name__)

CONFIG_PATH = Path("./data/category_config.json")


def load_category_config() -> dict[str, Any]:
    settings = get_settings()
    path = settings.data_dir / "category_config.json"
    if not path.exists() and CONFIG_PATH.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(CONFIG_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    if not path.exists():
        path = CONFIG_PATH
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            logger.warning("Invalid category_config.json: %s", exc)
    return {
        "auto_category_selection": True,
        "manual_category_id": None,
        "video_format_mode": "long",
        "category_weights": {cid: c.default_weight for cid, c in CATEGORIES.items()},
        "enabled_categories": list(CATEGORIES.keys()),
    }


def save_category_config(data: dict[str, Any]) -> None:
    settings = get_settings()
    path = settings.data_dir / "category_config.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
