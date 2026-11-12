from __future__ import annotations

from typing import Any

from app.config import get_settings


class CharacterManager:
    """Builds consistent character prompt fragments across scenes."""

    def __init__(self, story: dict[str, Any]) -> None:
        self.story = story
        self.settings = get_settings()
        self._chars = {c["name"]: c for c in story.get("characters", [])}

    def scene_prompt(self, scene: dict[str, Any]) -> str:
        base = scene.get("image_prompt") or scene.get("visual_description", "")
        traits = []
        for c in self.story.get("characters", []):
            traits.append(
                f"{c['name']}: {c.get('description', '')}, age {c.get('age_group', '')}"
            )
        consistency = "; ".join(traits)
        style = self.settings.image_style
        return (
            f"{style}. Scene: {base}. "
            f"Maintain same character faces and clothing throughout: {consistency}. "
            "No watermark, no captions in image."
        )

    def character_seed(self, key: str) -> int:
        return abs(hash(key)) % (2**31 - 1)
