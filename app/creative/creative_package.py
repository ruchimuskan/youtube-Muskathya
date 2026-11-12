from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class CreativePackageWriter:
    def __init__(self, root: Path) -> None:
        self.root = root / "creative_package"
        self.root.mkdir(parents=True, exist_ok=True)

    def save_all(self, package: dict[str, Any]) -> Path:
        mapping = {
            "voice_selection.json": package.get("voice_selection"),
            "voice_quality_report.json": package.get("voice_quality"),
            "music_selection.json": package.get("music_selection"),
            "sound_effects.json": package.get("sound_effects"),
            "thumbnail_concepts.json": package.get("thumbnail_concepts"),
            "title_candidates.json": package.get("title_candidates"),
            "selected_title.txt": package.get("selected_title", ""),
            "description_hi.txt": package.get("description", ""),
            "promotional_caption_hi.txt": package.get("promotional_caption", ""),
            "hashtags.txt": package.get("hashtags_text", ""),
            "video_tags.json": package.get("tags", []),
            "pinned_comment_hi.txt": package.get("pinned_comment", ""),
            "chapters.json": package.get("chapters"),
            "seo_report.json": package.get("seo_report"),
            "category_selection.json": package.get("category_selection"),
        }
        for name, data in mapping.items():
            dest = self.root / name
            if name.endswith(".txt"):
                dest.write_text(str(data or ""), encoding="utf-8")
            elif data is not None:
                dest.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        final_thumb = package.get("thumbnail_final_path")
        if final_thumb and Path(final_thumb).exists():
            import shutil

            shutil.copy(final_thumb, self.root / "thumbnail_final.jpg")
        return self.root
