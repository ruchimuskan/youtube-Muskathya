from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image

from app.config import get_settings
from app.utils.media_bins import probe_media_json

logger = logging.getLogger(__name__)


@dataclass
class QCResult:
    passed: bool
    checks: list[dict] = field(default_factory=list)
    critical_failures: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "checks": self.checks,
            "critical_failures": self.critical_failures,
        }


class QualityChecker:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _ffprobe(self, path: Path) -> dict:
        return probe_media_json(self.settings, path)

    def inspect_video(
        self,
        video_path: Path,
        *,
        expected_aspect: str,
        min_duration: float,
        max_duration: float,
        thumbnail_path: Path | None = None,
        title: str | None = None,
        story_complete: bool = True,
        language: str | None = None,
    ) -> QCResult:
        result = QCResult(passed=True)

        def add(name: str, ok: bool, detail: str, critical: bool = False):
            result.checks.append({"name": name, "passed": ok, "detail": detail})
            if not ok:
                if critical:
                    result.critical_failures.append(name)
                    result.passed = False

        if not video_path.exists():
            add("file_exists", False, "Video file missing", critical=True)
            return result

        try:
            meta = self._ffprobe(video_path)
        except Exception as exc:
            add("playable", False, str(exc), critical=True)
            return result

        duration = float(meta.get("format", {}).get("duration", 0))
        dur_ok = min_duration <= duration <= max_duration
        add(
            "duration",
            dur_ok,
            f"duration={duration:.1f}s",
            critical=min_duration >= 120,
        )

        vstreams = [s for s in meta.get("streams", []) if s.get("codec_type") == "video"]
        astreams = [s for s in meta.get("streams", []) if s.get("codec_type") == "audio"]
        add("video_stream", bool(vstreams), "video stream present", critical=not vstreams)
        add("audio_stream", bool(astreams), "audio stream present", critical=not astreams)

        if vstreams:
            w, h = int(vstreams[0].get("width", 0)), int(vstreams[0].get("height", 0))
            ratio = f"{w}:{h}" if h else ""
            if expected_aspect == "9:16":
                ok = h > w and w >= 1080
            else:
                ok = w >= h and w >= 1920 and h >= 1080
            add("aspect_ratio", ok, f"{w}x{h} ({ratio})", critical=expected_aspect == "16:9")

        if language == "hi" and title:
            has_devanagari = any("\u0900" <= ch <= "\u097f" for ch in title)
            add("hindi_title", has_devanagari, "title uses Devanagari", critical=False)

        if thumbnail_path:
            if thumbnail_path.exists():
                with Image.open(thumbnail_path) as im:
                    tw, th = im.size
                    readable = tw >= 640 and th >= 360
                add("thumbnail", readable, f"{tw}x{th}")
            else:
                add("thumbnail", False, "thumbnail missing", critical=True)

        add("story_complete", story_complete, "story marked complete")
        if title:
            add("title_present", len(title.strip()) > 0, "title set")

        return result
