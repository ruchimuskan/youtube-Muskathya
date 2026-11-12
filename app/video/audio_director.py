from __future__ import annotations

import logging
import random
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.content.categories import get_category

logger = logging.getLogger(__name__)

CATEGORY_MUSIC_HINTS: dict[str, list[str]] = {
    "horror": ["suspense", "dark", "horror", "mystery"],
    "emotional": ["emotional", "piano", "soft", "sad"],
    "moral": ["warm", "light", "hope", "moral"],
    "kids": ["playful", "kids", "happy", "gentle"],
    "royal": ["epic", "orchestral", "royal", "fantasy"],
    "inspirational": ["motivation", "uplift", "energy"],
    "adventure": ["adventure", "action", "cinematic"],
    "folk": ["folk", "traditional", "tabla"],
    "thriller": ["thriller", "tension", "pulse"],
    "village": ["acoustic", "village", "calm"],
}


class AudioDirector:
    """Pick BGM + annotate SFX hints per scene (mixing in AudioMixer)."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def scene_sfx_hints(self, category_id: str, story: dict[str, Any]) -> list[dict[str, Any]]:
        category = get_category(category_id)
        defaults = CATEGORY_MUSIC_HINTS.get(category.audio_profile, ["ambient", "story"])
        out = []
        for scene in story.get("scenes", []):
            mood = (scene.get("mood") or "").lower()
            hints = list(defaults)
            if "suspense" in mood or category.audio_profile in ("horror", "thriller"):
                hints += ["wind", "footsteps", "door"]
            if "emotional" in mood:
                hints += ["soft_ambience"]
            out.append(
                {
                    "scene_number": scene.get("scene_number"),
                    "sfx_hint": scene.get("sfx_hint"),
                    "music_keywords": hints,
                }
            )
        return out

    def pick_background_track(self, category_id: str, story: dict[str, Any]) -> Path | None:
        category = get_category(category_id)
        keywords = CATEGORY_MUSIC_HINTS.get(category.audio_profile, ["ambient"])
        music_dir = self.settings.background_music_dir
        if not music_dir.exists():
            return None
        candidates: list[Path] = []
        for ext in ("*.mp3", "*.wav", "*.ogg", "*.m4a"):
            candidates.extend(music_dir.rglob(ext))
        if not candidates:
            return None
        scored: list[tuple[int, Path]] = []
        for p in candidates:
            name = p.stem.lower()
            score = sum(1 for k in keywords if k in name)
            scored.append((score, p))
        scored.sort(key=lambda x: (-x[0], x[1].name))
        top_score = scored[0][0]
        pool = [p for s, p in scored if s == top_score] or candidates
        choice = random.choice(pool)
        return choice

    def build_selection_report(
        self, category_id: str, track: Path | None, scene_hints: list[dict]
    ) -> dict[str, Any]:
        return {
            "category_id": category_id,
            "background_track": str(track) if track else None,
            "license_note": "User must place royalty-free tracks in data/music/",
            "scene_audio_plan": scene_hints,
        }
