from __future__ import annotations

import logging
import random
import subprocess
from pathlib import Path

from app.config import get_settings
from app.utils.media_bins import resolve_ffmpeg_bin

logger = logging.getLogger(__name__)

MOOD_FILES = {
    "suspense": ["suspense", "dark", "tension"],
    "emotional": ["emotional", "sad", "hope"],
    "peaceful": ["peaceful", "calm", "soft"],
    "dramatic": ["dramatic", "epic", "climax"],
    "default": ["ambient", "story", "default"],
}


class AudioMixer:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._ffmpeg = resolve_ffmpeg_bin(self.settings)

    def _pick_bgm(self, story: dict) -> Path | None:
        music_dir = self.settings.background_music_dir
        if not music_dir.exists():
            return None
        moods = {s.get("mood", "").lower() for s in story.get("scenes", []) if s.get("mood")}
        keywords: set[str] = set()
        for m in moods:
            for k, tags in MOOD_FILES.items():
                if k in m or any(t in m for t in tags):
                    keywords.update(tags)
        if not keywords:
            keywords = set(MOOD_FILES["default"])

        candidates: list[Path] = []
        for ext in ("*.mp3", "*.wav", "*.m4a", "*.ogg"):
            candidates.extend(music_dir.rglob(ext))
        if not candidates:
            return None

        scored: list[tuple[int, Path]] = []
        for p in candidates:
            name = p.stem.lower()
            score = sum(1 for k in keywords if k in name)
            scored.append((score, p))
        scored.sort(key=lambda x: (-x[0], x[1].name))
        top = [p for s, p in scored if s == scored[0][0]] or candidates
        return random.choice(top)

    def mix_narration_with_bgm(
        self,
        narration_wav: Path,
        work_dir: Path,
        story: dict,
    ) -> Path:
        bgm = self._pick_bgm(story)
        out = work_dir / "narration_with_bgm.wav"
        if not bgm:
            logger.info("No background music in %s; narration only", self.settings.background_music_dir)
            return narration_wav

        narration_vol = self.settings.narration_volume
        music_vol = self.settings.background_music_volume
        cmd = [
            self._ffmpeg,
            "-y",
            "-i",
            str(narration_wav),
            "-stream_loop",
            "-1",
            "-i",
            str(bgm),
            "-filter_complex",
            (
                f"[0:a]volume={narration_vol}[n];"
                f"[1:a]volume={music_vol},afade=t=in:st=0:d=2,afade=t=out:st=0:d=3[bg];"
                f"[n][bg]amix=inputs=2:duration=first:dropout_transition=2[aout]"
            ),
            "-map",
            "[aout]",
            "-c:a",
            "pcm_s16le",
            str(out),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return out
