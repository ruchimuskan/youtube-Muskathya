from __future__ import annotations

from pathlib import Path

from app.config import get_settings


def canonical_thumbnail_path(story_id: int | None) -> Path:
    """Global thumbnails/ folder name used before YouTube upload."""
    settings = get_settings()
    root = settings.output_dir / "thumbnails"
    root.mkdir(parents=True, exist_ok=True)
    sid = story_id or 0
    return root / f"story_{sid:03d}_thumbnail.jpg"


def story_thumbnail_in_workdir(work_dir: Path, story_id: int | None) -> Path:
    sid = story_id or 0
    return work_dir / "thumbnail" / f"story_{sid:03d}_thumbnail.jpg"
