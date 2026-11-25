from __future__ import annotations

from typing import Any

from app.config import get_settings


def build_sdxl_prompt(story: dict[str, Any], scene: dict[str, Any]) -> str:
    """
    Constructs high-impact cinematic Bollywood image prompt matching exact story events
    with persistent character features.
    """
    settings = get_settings()
    story_style = story.get("visual_style") or settings.image_style
    visual = (scene.get("visual_description") or scene.get("image_prompt") or "").strip()
    mood = (scene.get("mood") or "suspense").strip()

    # Identify character in this scene
    char_refs = story.get("character_references") or story.get("characters") or []
    char_map = {c.get("name"): c for c in char_refs if isinstance(c, dict)}

    active_name = None
    for d in scene.get("dialogue") or []:
        spk = d.get("character")
        if spk and spk in char_map:
            active_name = spk
            break
    if not active_name and scene.get("characters_present"):
        active_name = scene["characters_present"][0]
    if not active_name and char_refs:
        active_name = char_refs[0].get("name")

    char_details = ""
    if active_name and active_name in char_map:
        c = char_map[active_name]
        phys = c.get("physical_appearance") or c.get("description") or "expressive Indian features"
        attire = c.get("signature_attire") or "authentic attire"
        char_details = f"character {active_name}: {phys[:75]}, {attire[:60]}."

    parts = [
        "ultra-realistic cinematic 35mm photograph, photorealistic Bollywood thriller cinematography,",
        f"{mood} mood,",
        story_style,
        visual[:220],
    ]
    if char_details:
        parts.append(char_details)
    parts.append("dramatic lighting, shallow depth of field, detailed expressive face, natural skin texture, 8k.")
    text = " ".join(parts)
    return text[:380]
