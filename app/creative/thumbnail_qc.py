from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageStat

from app.images.image_validator import is_valid_scene_image

logger = logging.getLogger(__name__)

YOUTUBE_THUMB_SIZE = (1280, 720)


@dataclass
class ThumbnailQCResult:
    passed: bool
    issues: list[str] = field(default_factory=list)

    def fail(self, name: str, detail: str) -> None:
        self.issues.append(f"{name}: {detail}")
        self.passed = False


def validate_thumbnail(
    path: Path,
    *,
    analysis: dict | None = None,
    expected_headline: str | None = None,
) -> ThumbnailQCResult:
    res = ThumbnailQCResult(passed=True)
    if not path.exists():
        res.fail("exists", "file missing")
        return res
    if not is_valid_scene_image(path):
        res.fail("quality", "image too small, corrupt, or flat")
        return res
    with Image.open(path) as im:
        im = im.convert("RGB")
        if im.size != YOUTUBE_THUMB_SIZE:
            res.fail("dimensions", f"expected 1280x720, got {im.size}")
        stat = ImageStat.Stat(im)
        mean_brightness = sum(stat.mean[:3]) / 3
        if mean_brightness < 18:
            res.fail("brightness", "too dark for YouTube")
        if analysis:
            headline = (analysis.get("hindi_headline") or "").strip()
            if headline and not any("\u0900" <= c <= "\u097f" for c in headline):
                res.fail("hindi_headline", "missing Devanagari")
            if "**" in headline or "*" in headline:
                res.fail("markdown", "markdown in headline metadata")
        if expected_headline and "**" in expected_headline:
            res.fail("markdown", "markdown in expected headline")
    return res
