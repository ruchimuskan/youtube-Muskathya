from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageStat

from app.config import get_settings


def is_valid_scene_image(path: Path) -> bool:
    settings = get_settings()
    if not path.exists():
        return False
    if path.stat().st_size < settings.image_min_file_bytes:
        return False
    try:
        with Image.open(path) as im:
            im = im.convert("RGB")
            w, h = im.size
            if w < 960 or h < 540:
                return False
            stat = ImageStat.Stat(im)
            # Reject near-solid fallback plates (low channel variance)
            if all(s < 12 for s in stat.stddev[:3]):
                return False
    except OSError:
        return False
    return True
