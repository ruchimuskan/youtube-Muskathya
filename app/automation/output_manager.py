from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class OutputManager:
    """Structured story export folders."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.dirs = {
            "images": root / "images",
            "audio": root / "audio",
            "subtitles": root / "subtitles",
            "thumbnail": root / "thumbnail",
            "final": root / "final",
        }
        for d in self.dirs.values():
            d.mkdir(parents=True, exist_ok=True)

    def save_full_story_json(self, story: dict[str, Any]) -> Path:
        """Single file with the complete generated story (scenes, dialogue, metadata)."""
        payload = {
            "story_project_id": story.get("story_project_id"),
            "title": story.get("title"),
            "language": story.get("language"),
            "genre": story.get("genre"),
            "content_category_id": story.get("content_category_id"),
            "target_duration_sec": story.get("target_duration_sec"),
            "is_short": story.get("is_short"),
            "story": story,
        }
        path = self.root / "story.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def save_story_artifacts(
        self,
        story: dict[str, Any],
        *,
        seo: dict[str, Any] | None = None,
        image_prompts: list[dict] | None = None,
    ) -> None:
        self.save_full_story_json(story)

        script_lines = [story.get("hook_opening", ""), ""]
        for scene in story.get("scenes", []):
            script_lines.append(scene.get("narration", ""))
        script_lines.append(story.get("call_to_action") or story.get("ending", ""))
        (self.root / "script_hindi.txt").write_text(
            "\n\n".join(s for s in script_lines if s), encoding="utf-8"
        )

        (self.root / "scene_breakdown.json").write_text(
            json.dumps(story.get("scenes", []), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        chars = story.get("characters") or story.get("character_references")
        if chars:
            (self.root / "character_references.json").write_text(
                json.dumps(chars, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        if image_prompts:
            (self.root / "image_prompts.json").write_text(
                json.dumps(image_prompts, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        if seo:
            (self.root / "youtube_metadata.json").write_text(
                json.dumps(seo, ensure_ascii=False, indent=2), encoding="utf-8"
            )
