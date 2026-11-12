from __future__ import annotations

from typing import Any

from app.config import get_settings


def build_sdxl_prompt(story: dict[str, Any], scene: dict[str, Any]) -> str:
    """Compact English prompt — SDXL works best under ~280 characters."""
    settings = get_settings()
    story_style = story.get("visual_style") or settings.image_style
    visual = (scene.get("visual_description") or scene.get("image_prompt") or "").strip()
    mood = (scene.get("mood") or "dramatic").strip()
    chars = story.get("characters") or []
    lead = chars[0] if chars else {}
    lead_desc = (lead.get("description") or "")[:80]
    lead_name = lead.get("name", "hero")

    parts = [
        "masterpiece, best quality, cinematic Indian story illustration,",
        f"{mood} mood,",
        story_style,
        visual[:220],
    ]
    if lead_desc:
        parts.append(f"main character {lead_name}: {lead_desc}.")
    parts.append("single clear focal subject, detailed expressive face, natural proportions.")
    text = " ".join(parts)
    return text[:380]
