from __future__ import annotations

import json
import logging
from typing import Any

from app.ai.providers import LLMRouter
from app.content.categories import get_category

logger = logging.getLogger(__name__)

ANALYSIS_SCHEMA = """
{
  "main_characters": [{"name": "...", "appearance_en": "...", "expression": "...", "pose_action": "..."}],
  "key_object": "specific gift/mystery object from story — exact as in narration",
  "best_scene_number": 1,
  "focal_moment_en": "one sentence — the most clickable visual beat",
  "emotional_hook": "primary emotion",
  "suspense_element": "what question viewer should have",
  "background_en": "environment matching story",
  "camera_angle": "close-up | wide | low angle | over-shoulder",
  "character_placement": "who left/center/right",
  "art_prompt_en": "80-120 word SDXL prompt: 3D cinematic YouTube thumbnail, expressive faces, lighting",
  "hindi_headline": "3-7 words Devanagari, no ending spoiler",
  "hindi_suspense": "optional 3-6 words curiosity phrase",
  "text_color_scheme": "gold|white|red",
  "why_this_moment": "brief"
}
"""


class StoryThumbnailAnalyzer:
    """Deep story JSON analysis before any image is generated."""

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
                "characters": story.get("characters") or story.get("character_references"),
                "scenes": [
                    {
                        "scene_number": s.get("scene_number"),
                        "story_beat": s.get("story_beat"),
                        "mood": s.get("mood"),
                        "narration": s.get("narration"),
                        "visual_description": s.get("visual_description"),
                        "dialogue": s.get("dialogue"),
                    }
                    for s in (story.get("scenes") or [])
                ],
            },
            ensure_ascii=False,
        )[:14_000]

        prompt = f"""You are a senior YouTube thumbnail director for Hindi story channels.

Analyze this COMPLETE story and plan ONE premium thumbnail (not a random first scene).

Category: {category.name_hi} ({category.name_en})
Audience: {category.audience}
Genre tone: {category.thumbnail_tone}
Visual world: {category.visual_style}

Story JSON:
{story_blob}

Rules:
- Pick best_scene_number with the strongest visual + emotional + suspense impact (often climax/suspense, NOT scene 1).
- For Hindu mythology with Shiva/Ganesha: appearance_en MUST describe authentic deities (blue Shiva, elephant-head Ganesha), NEVER modern humans.
- key_object must match narration exactly (candle stays candle).
- art_prompt_en: 3D CGI YouTube thumbnail, medium close-up, characters 60% of frame, NOT empty landscape.
- hindi_headline and hindi_suspense are optional hints only (overlay added separately); use empty string if unsure.
- Do NOT use unrelated clickbait.

Return JSON only matching schema:
{ANALYSIS_SCHEMA}
"""
        response = self.llm.complete(
            prompt,
            system="Valid JSON only. hindi fields in Devanagari.",
            json_mode=True,
        )
        data = self.llm.parse_json(response.text)
        for key in ("hindi_headline", "hindi_suspense"):
            if isinstance(data.get(key), str):
                data[key] = data[key].replace("**", "").replace("*", "").strip()
        data["category_id"] = category_id
        data["story_title"] = story.get("title")
        logger.info(
            "Thumbnail analysis scene=%s object=%s",
            data.get("best_scene_number"),
            data.get("key_object"),
        )
        return data
