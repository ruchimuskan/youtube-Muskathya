from __future__ import annotations

import json
import logging
from typing import Any

from app.ai.providers import LLMRouter
from app.content.categories import get_category

logger = logging.getLogger(__name__)

GENRE_VISUAL_PROFILES: dict[str, dict[str, str]] = {
    "suspense": {
        "lighting": "dramatic chiaroscuro rim lighting, razor-sharp edge light, deep cold blue and charcoal shadows",
        "atmosphere": "tense, breathless, high psychological suspense, intense eye reflections",
        "color_palette": "deep midnight blue, slate, charcoal, and warm piercing amber highlights",
    },
    "mystery": {
        "lighting": "volumetric moonlight shafts through thick atmospheric mist, dramatic lantern glow in shadows",
        "atmosphere": "eerie curiosity, ancient haveli secrets, shadowy silhouette, hidden clues",
        "color_palette": "smoky teal, moody cyan, dark stone grey, and glowing brass lantern gold",
    },
    "horror": {
        "lighting": "harsh macabre moonlight, deep pitch-black shadows, eerie cold rim lighting",
        "atmosphere": "chilling dread, ancient Indian haveli, sudden shock, terrifying revelation",
        "color_palette": "cold decaying desaturated blue, deep black, and ominous crimson accents",
    },
    "emotional": {
        "lighting": "warm soft natural cinematic window light, gentle rim lighting catching glistening tears",
        "atmosphere": "raw heartfelt emotional confrontation, poignant heartbreak, intimate family drama",
        "color_palette": "warm amber, soft terracotta, deep earthy wood tones, and gentle gold",
    },
    "family": {
        "lighting": "authentic Indian home lighting, dramatic depth of field between foreground and background characters",
        "atmosphere": "emotional confrontation, shattered trust, shocked parents in background",
        "color_palette": "rich natural warm Indian palette, golden hour highlights, textured fabrics",
    },
    "thriller": {
        "lighting": "stark high-contrast noir lighting, razor-sharp highlights, extreme visual tension",
        "atmosphere": "heart-pounding danger, dramatic betrayal unmasked, breathless chase",
        "color_palette": "high contrast, deep carbon black, cold steel blue, and vibrant crimson",
    },
    "motivational": {
        "lighting": "epic golden dawn backlight, hopeful rim light, sunbeams piercing through storm clouds",
        "atmosphere": "unbreakable human determination, hard-earned triumph, sweat and resilience",
        "color_palette": "golden sunrise amber, rich saffron, warm earthy terracotta",
    },
}

ANALYSIS_SCHEMA = """
{
  "best_scene_number": 1,
  "focal_moment_en": "one vivid sentence describing the exact peak turning point or shocking discovery",
  "genre_style": "suspense | mystery | horror | emotional | family | thriller | motivational",
  "lead_character": {
    "name": "character name",
    "position": "left foreground | right foreground",
    "facial_expression": "intense shocked expression with wide eyes | glistening tears of betrayal",
    "pose_action": "holding a glowing brass lantern | reading a blood-stained letter with trembling hands",
    "appearance_en": "exact physical description matching story character sheet"
  },
  "supporting_element": {
    "description": "mysterious silhouette standing in shadowy doorway | shocked mother in background",
    "position": "opposite side in midground"
  },
  "key_story_object": "exact physical object from story (brass lantern, yellowed letter, broken silver locket)",
  "environment_background": "ancient Indian haveli with decaying stone arches and moonlight | authentic middle-class Indian living room",
  "camera_framing": "cinematic medium close-up, 35mm anamorphic lens, rule of thirds, shallow depth of field",
  "hindi_headline": "2-5 words high curiosity Devanagari hook",
  "hindi_suspense": "optional 2-4 words supporting Devanagari phrase"
}
"""


class StoryThumbnailAnalyzer:
    """
    Analyzes the complete story to direct a high-CTR, ChatGPT-quality Bollywood movie poster thumbnail.
    Derives character placement, story-specific visual anchors, cinematic lighting, and mobile-optimized copy.
    """

    def __init__(self, llm: LLMRouter | None = None) -> None:
        self.llm = llm or LLMRouter()

    def analyze(self, story: dict[str, Any], category_id: str) -> dict[str, Any]:
        category = get_category(category_id)
        story_blob = json.dumps(
            {
                "title": story.get("title"),
                "synopsis": story.get("synopsis"),
                "hook_opening": story.get("hook_opening"),
                "ending": story.get("ending"),
                "conclusion_moral": story.get("conclusion_moral"),
                "characters": story.get("characters") or story.get("character_references"),
                "scenes": [
                    {
                        "scene_number": s.get("scene_number"),
                        "story_beat": s.get("story_beat"),
                        "mood": s.get("mood"),
                        "narration": s.get("narration"),
                        "visual_description": s.get("visual_description"),
                    }
                    for s in (story.get("scenes") or [])
                ],
            },
            ensure_ascii=False,
        )[:15_000]

        prompt = f"""You are an elite Bollywood Movie Poster Art Director and YouTube CTR Optimization Specialist.

Analyze this COMPLETE Hindi story and plan ONE cinematic, movie-poster-level thumbnail concept.

Story Category: {category.name_hi} ({category.name_en})
Audience: {category.audience}
Story JSON:
{story_blob}

CRITICAL ART DIRECTION RULES:
1. Identify the single most dramatic, shocking, emotional, or mysterious turning point in the story (often the twist, climax, or chilling discovery, NOT a boring opening scene).
2. Lead character must have ultra-realistic Indian facial features, authentic skin texture, and intense, genuine emotional expression (shock, terror, tears, or fierce confrontation).
3. Composition: Position the main subject on one third of the frame (left or right), with the secondary mystery element or opposing character in the opposite depth, and the story location in the background.
4. Key story object: Must be an exact tangible object from the story narration (lantern, letter, locked wooden box, old photograph).
5. Lighting: Dramatic Bollywood thriller poster lighting matching the story genre (chiaroscuro, rim light, atmospheric volumetrics). Never force horror lighting onto warm emotional stories.
6. NO TEXT in the artwork: The art prompt must request zero text, zero letters, zero watermarks.
7. hindi_headline: 2 to 5 words Devanagari Hindi curiosity hook with maximum click-through appeal (e.g. 'आखिर सच क्या था?', 'उस कमरे में कौन था?', '20 साल पुराना रहस्य').

Return JSON matching schema:
{ANALYSIS_SCHEMA}
"""
        data: dict[str, Any]
        try:
            response = self.llm.complete(
                prompt,
                system="You are a master Bollywood movie poster art director. Output valid JSON only.",
                json_mode=True,
            )
            data = self.llm.parse_json(response.text)
        except Exception as exc:
            logger.warning("Thumbnail analyzer LLM failed: %s. Using procedural Bollywood concept.", exc)
            data = self._procedural_fallback(story, category_id)

        data["category_id"] = category_id
        data["story_title"] = story.get("title")
        data["genre_profile"] = self._resolve_genre_profile(
            data.get("genre_style") or story.get("genre") or category_id
        )
        data["art_prompt_en"] = self.build_detailed_poster_prompt(story, data)

        logger.info(
            "Thumbnail analysis complete: scene=%s object=%s headline=%s",
            data.get("best_scene_number"),
            data.get("key_story_object"),
            data.get("hindi_headline"),
        )
        return data

    def _resolve_genre_profile(self, genre_hint: str) -> dict[str, str]:
        hint = genre_hint.lower()
        if "horror" in hint or "ghost" in hint or "bhoot" in hint:
            return GENRE_VISUAL_PROFILES["horror"]
        if "motivat" in hint or "inspir" in hint or "prerna" in hint:
            return GENRE_VISUAL_PROFILES["motivational"]
        if "emotion" in hint or "sad" in hint or "heart" in hint:
            return GENRE_VISUAL_PROFILES["emotional"]
        if "family" in hint or "parivar" in hint or "rishte" in hint:
            return GENRE_VISUAL_PROFILES["family"]
        if "thrill" in hint or "action" in hint:
            return GENRE_VISUAL_PROFILES["thriller"]
        if "myster" in hint or "village" in hint or "rahasya" in hint or "haveli" in hint:
            return GENRE_VISUAL_PROFILES["mystery"]
        for k, prof in GENRE_VISUAL_PROFILES.items():
            if k in hint:
                return prof
        return GENRE_VISUAL_PROFILES["suspense"]

    def build_detailed_poster_prompt(self, story: dict[str, Any], analysis: dict[str, Any]) -> str:
        """
        Constructs an ultra-detailed 12-component Bollywood poster prompt
        suitable for DALL-E 3 and Cloudflare SDXL/Flux.
        """
        lead = analysis.get("lead_character") or {}
        char_name = lead.get("name") or "lead protagonist"
        char_desc = lead.get("appearance_en") or "expressive Indian features with textured clothing"
        char_pos = lead.get("position") or "left foreground"
        char_expr = lead.get("facial_expression") or "shocked and intense expression"
        char_pose = lead.get("pose_action") or "reaching forward with intense focus"

        support = analysis.get("supporting_element") or {}
        supp_desc = support.get("description") or "mysterious shadowy silhouette in background"
        supp_pos = support.get("position") or "right midground"

        key_obj = analysis.get("key_story_object") or "revealing mysterious clue"
        env = analysis.get("environment_background") or "authentic atmospheric Indian setting"
        framing = analysis.get("camera_framing") or "cinematic 35mm photograph, medium close-up, rule of thirds"

        genre_prof = analysis.get("genre_profile") or self._resolve_genre_profile(story.get("genre", "suspense"))
        lighting = genre_prof["lighting"]
        atmosphere = genre_prof["atmosphere"]
        palette = genre_prof["color_palette"]

        prompt = (
            f"Ultra-realistic cinematic Bollywood movie poster photograph. {framing}. "
            f"In the {char_pos}, an Indian character {char_name}: {char_desc}, {char_expr}, {char_pose}. "
            f"In the {supp_pos}, {supp_desc}. "
            f"Focal story element: {key_obj}. "
            f"Environment: {env}. "
            f"Lighting: {lighting}. "
            f"Atmosphere: {atmosphere}. "
            f"Color grading: {palette}. "
            "Hyperrealistic skin textures, natural human eyes, anamorphic lens flare, shallow depth of field, 8k resolution. "
            "ABSOLUTELY NO TEXT, NO LETTERS, NO WORDS, NO TYPOGRAPHY, NO WATERMARKS, NO BORDERS, NO CARTOON, NO CGI."
        )
        return prompt[:3800]

    def _procedural_fallback(self, story: dict[str, Any], category_id: str) -> dict[str, Any]:
        """High-grade procedural concept when LLM is unavailable."""
        title = (story.get("title") or "सच्चाई का खुलासा").split("|")[0].strip()
        chars = story.get("characters") or story.get("character_references") or []
        first_char = chars[0] if chars else {}
        name = first_char.get("name", "नायक")
        desc = first_char.get("description", "Indian youth with intense eyes")

        from app.creative.hindi_thumbnail_copy import derive_story_curiosity_hook

        hook = derive_story_curiosity_hook(story)

        return {
            "best_scene_number": 1,
            "focal_moment_en": "Main character discovering the shocking hidden truth",
            "genre_style": category_id,
            "lead_character": {
                "name": name,
                "position": "left foreground",
                "facial_expression": "wide shocked eyes and intense emotional expression",
                "pose_action": "holding a key story object in trembling hands",
                "appearance_en": desc,
            },
            "supporting_element": {
                "description": "dark shadowy figure looming in the background doorway",
                "position": "right background",
            },
            "key_story_object": "crucial revealing clue",
            "environment_background": "atmospheric Indian location at stormy night",
            "camera_framing": "cinematic medium close-up, 35mm film still, shallow depth of field",
            "hindi_headline": hook,
            "hindi_suspense": "",
        }
