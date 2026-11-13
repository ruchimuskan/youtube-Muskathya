from __future__ import annotations

import re
from typing import Any

SHIVA_VISUAL_EN = (
    "Lord Shiva, blue-skinned divine deity, long dark matted jata hair, crescent moon on forehead, "
    "third eye, rudraksha mala, serpent around neck, traditional divine attire, trishul nearby, "
    "peaceful powerful expression, clearly recognizable Hindu god Shiva, NOT a modern human man"
)

GANESHA_VISUAL_EN = (
    "Lord Ganesha, elephant head with large ears and curved trunk, one broken tusk, golden crown, "
    "divine ornaments, adorable childlike divine body, joyful curious eyes, "
    "clearly recognizable Hindu god Ganesha, NEVER a human face, NOT an ordinary boy"
)

MYTHOLOGY_CATEGORIES = frozenset(
    {"mythology_inspired", "folk_mythology", "royal", "adventure"}
)

THUMB_NEGATIVE_EXTRA = (
    "text, letters, words, numbers, watermark, logo, caption, markdown, asterisks, "
    "modern clothing, jeans, dress, suit, sneakers, western fashion, red dress, belt, "
    "stock photo, realistic photograph, hikers, tourists, random woman, random man, "
    "ordinary humans, human faces only, empty landscape, tiny distant people, "
    "small figures in corner, aerial valley only, no deities, extra limbs, deformed, blurry, ugly"
)


def _story_text(story: dict[str, Any]) -> str:
    title = story.get("title") or ""
    names = " ".join(
        c.get("name", "") for c in (story.get("characters") or []) if isinstance(c, dict)
    )
    return f"{title} {names}"


def story_has_shiva_ganesha(story: dict[str, Any]) -> bool:
    blob = _story_text(story).lower()
    return bool(re.search(r"शिव|shiva", blob, re.I)) and bool(
        re.search(r"गणेश|ganesha|ganesh", blob, re.I)
    )


def story_has_shiva(story: dict[str, Any]) -> bool:
    return bool(re.search(r"शिव|shiva", _story_text(story), re.I))


def story_has_ganesha(story: dict[str, Any]) -> bool:
    return bool(re.search(r"गणेश|ganesha|ganesh", _story_text(story), re.I))


def apply_character_bible(story: dict[str, Any], category_id: str, analysis: dict[str, Any]) -> dict[str, Any]:
    """Replace weak LLM human descriptions with strict visual canon when recognizable."""
    analysis = dict(analysis)
    chars: list[dict[str, Any]] = []

    if story_has_shiva_ganesha(story) or (
        category_id in MYTHOLOGY_CATEGORIES and story_has_shiva(story) and story_has_ganesha(story)
    ):
        chars = [
            {
                "name": "Lord Shiva",
                "appearance_en": SHIVA_VISUAL_EN,
                "expression": "loving peaceful divine father",
                "pose_action": "on the LEFT, extending both hands presenting a glowing divine candle gift toward Ganesha",
            },
            {
                "name": "Lord Ganesha",
                "appearance_en": GANESHA_VISUAL_EN,
                "expression": "surprised happy curious",
                "pose_action": "on the RIGHT, leaning toward Shiva, gazing at the glowing candle",
            },
        ]
        analysis["main_characters"] = chars
        analysis["character_placement"] = "Shiva left, Ganesha right, candle centered between them"
        analysis["camera_angle"] = "medium close-up"
        analysis["background_en"] = (
            "Mount Kailash Himalaya peaks, divine golden light rays, magical particles, "
            "misty sacred atmosphere, NOT empty tourist valley"
        )
        analysis["key_object"] = (
            "beautiful glowing divine candle (mystical wax flame with golden aura) — central highlight"
        )
        analysis["composition_notes"] = (
            "Two deities fill 65% of frame; candle at center foreground; faces large and sharp"
        )
        analysis["best_scene_number"] = analysis.get("best_scene_number") or 5
        analysis["focal_moment_en"] = (
            analysis.get("focal_moment_en")
            or "Shiva presents a glowing divine candle to elephant-headed Ganesha on Kailash"
        )
    elif category_id in MYTHOLOGY_CATEGORIES and story_has_shiva(story):
        chars.append(
            {
                "name": "Lord Shiva",
                "appearance_en": SHIVA_VISUAL_EN,
                "expression": analysis.get("emotional_hook", "divine calm"),
                "pose_action": "dominant close-up hero pose",
            }
        )
        analysis["main_characters"] = chars + list(analysis.get("main_characters") or [])[:2]

    return analysis


def build_composition_block(analysis: dict[str, Any], category_id: str) -> str:
    notes = analysis.get("composition_notes") or ""
    return (
        "COMPOSITION: premium YouTube mythology thumbnail, medium close-up, characters occupy 60% of frame, "
        "strong foreground-background separation, clear emotional faces, key object visible and glowing. "
        f"{notes} "
        "AVOID: empty landscape, tiny people at edges, modern humans, photorealistic hikers. "
        f"Category tone: {category_id}."
    )
