from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from app.ai.providers import LLMRouter
from app.ai.topic_researcher import TopicResearcher
from app.config import get_settings
from app.content.categories import category_story_block, get_category
from app.database import Repository, session_scope

logger = logging.getLogger(__name__)

STORY_SCHEMA_HINT = """
{
  "title": "string (Hindi Devanagari if language is hi)",
  "synopsis": "string",
  "characters": [
    {"name": "...", "gender": "male|female", "age_group": "...", "description": "visual traits for consistency", "voice_id_hint": "..."}
  ],
  "character_references": "same as characters — detailed visual identity per character",
  "scenes": [
    {
      "scene_number": 1,
      "story_beat": "hook|intro|development|suspense|climax|ending",
      "duration_estimate_sec": 18,
      "visual_description": "English cinematic image prompt for this exact moment",
      "image_prompt": "optional extra English prompt",
      "narration": "Hindi Devanagari narrator lines",
      "dialogue": [{"character": "name", "line": "Hindi Devanagari", "gender": "male|female"}],
      "mood": "peaceful|emotional|suspense|dramatic",
      "sfx_hint": "optional"
    }
  ],
  "hook_opening": "first 5-10 seconds Hindi Devanagari",
  "ending": "satisfying Hindi conclusion",
  "call_to_action": "अगर आपको यह कहानी पसंद आई, तो वीडियो को लाइक करें और ऐसी ही कहानियों के लिए चैनल को सब्सक्राइब करें।",
  "content_rating": "general|children",
  "synthetic_disclosure_needed": true
}
"""


@dataclass
class StoryGenerationRequest:
    language: str
    genre: str
    target_duration_sec: int
    is_short: bool
    content_style: str = "cinematic Hindi storytelling"
    category_id: str = "moral"
    topic_research: dict[str, Any] | None = None
    min_scenes: int | None = None
    max_scenes: int | None = None
    visual_style: str | None = None


class StoryGenerator:
    def __init__(self, llm: LLMRouter | None = None) -> None:
        self.llm = llm or LLMRouter()
        self.topics = TopicResearcher(self.llm)
        self.settings = get_settings()

    def _lessons_block(self) -> str:
        with session_scope() as session:
            lessons = Repository(session).get_recent_lessons(20)
        if not lessons:
            return "No prior lessons."
        return "\n".join(f"- ({l.category}) {l.lesson}" for l in lessons)

    def _hindi_system(self) -> str:
        return (
            "You are an expert Hindi cinematic storyteller for YouTube with high audience retention. "
            "Stories must feel alive: conflict, surprise, emotion, dialogue — never flat preaching. "
            "All narration, dialogue, titles, hook and ending MUST be in natural Hindi (Devanagari). "
            "visual_description and image_prompt MUST be in English for AI image generation. "
            "Output only valid JSON."
        )

    def generate(self, req: StoryGenerationRequest) -> dict[str, Any]:
        topic = req.topic_research or self.topics.suggest_topic(req.language, req.genre, req.is_short)
        lessons = self._lessons_block()
        category = get_category(req.category_id)
        cat_block = category_story_block(category)
        min_scenes = req.min_scenes or self.settings.story_min_scenes
        max_scenes = req.max_scenes or self.settings.story_max_scenes

        if req.is_short:
            scene_cap = "exactly 4 to 5 scenes"
            brevity = (
                "Total 30-60 seconds spoken. Short Hindi lines. "
                "visual_description under 30 English words."
            )
        elif req.target_duration_sec >= 300:
            minutes_lo = max(req.target_duration_sec // 60, 5)
            scene_cap = f"{min_scenes} to {max_scenes} scenes"
            brevity = (
                f"Target {minutes_lo}-8 minutes of Hindi narration (~{req.target_duration_sec}s audio). "
                f"Use {scene_cap} with ONE distinct visual per scene. "
                "Each scene 20-35 seconds of spoken Hindi (5-7 natural sentences, min ~100 Devanagari chars). "
                "Structure: hook → intro → development → emotional/suspense beat → climax → ending → CTA. "
                "Never repeat the same visual_description. "
                "visual_description: detailed English, Indian setting when relevant."
            )
        else:
            scene_cap = "6 to 10 scenes"
            brevity = "Keep visual_description under 40 English words per scene."

        lang_rules = ""
        if req.language == "hi":
            lang_rules = """
- Hindi Devanagari ONLY for narration, dialogue, title, synopsis, hook, ending, call_to_action
- Natural emotional Hindi, not translated English
- Pronounce-friendly sentences for TTS
- Include call_to_action field in Hindi
"""

        prompt = f"""Write a completely original {req.genre} story for YouTube.
Language: {req.language}
Content category: {category.name_hi}
Target narration duration: ~{req.target_duration_sec} seconds
Format: {"vertical Short (9:16)" if req.is_short else "landscape cinematic long-form (16:9)"}
Style: {req.content_style}

{cat_block}

Visual style hint: {req.visual_style or category.visual_style}

Topic research:
{topic}

Apply lessons:
{lessons}

{lang_rules}

Requirements:
- Use {scene_cap}
- {brevity}
- RETENTION (critical for YouTube reach):
  * Open with a curiosity gap in hook_opening — a shocking question or unfinished moment
  * Each scene ends with a mini-cliffhanger or emotional turn (viewer wants the next scene)
  * At least one unexpected twist or reversal before climax — avoid predictable moral lectures
  * Use vivid dialogue between characters, not only narrator monologue
  * Relatable Indian settings, names, and emotions; avoid generic filler lines
  * Title must spark click curiosity in Hindi without clickbait lies
- Strong hook in first 5-10 seconds (pattern interrupt)
- Character visual descriptions for consistency across all scenes
- Children-safe if genre is children
- Original work only
- Valid JSON only

Schema:
{STORY_SCHEMA_HINT}
"""

        story = None
        last_err: Exception | None = None
        system = self._hindi_system() if req.language == "hi" else "You are an expert screenwriter. Output only valid JSON."

        for attempt in range(3):
            extra = ""
            if attempt > 0:
                extra = (
                    "\nIMPORTANT: Previous output was invalid JSON. "
                    "Return smaller JSON with fewer scenes and shorter strings."
                )
            response = self.llm.complete(
                prompt + extra,
                system=system,
                json_mode=True,
            )
            try:
                story = self.llm.parse_json(response.text)
                break
            except Exception as exc:
                last_err = exc
                logger.warning("Story JSON parse failed (attempt %s): %s", attempt + 1, exc)
        if story is None:
            raise ValueError(f"Failed to parse story JSON after retries: {last_err}") from last_err

        story["research"] = topic
        story["content_category_id"] = req.category_id
        story["content_category_name"] = category.name_hi
        story["visual_style"] = req.visual_style or category.visual_style
        story["language"] = req.language
        story["genre"] = req.genre
        story["is_short"] = req.is_short
        story["target_duration_sec"] = req.target_duration_sec
        if req.language == "hi" and not story.get("call_to_action"):
            story["call_to_action"] = (
                "अगर आपको यह कहानी पसंद आई, तो वीडियो को लाइक करें "
                "और ऐसी ही कहानियों के लिए चैनल को सब्सक्राइब करें।"
            )

        if not story.get("scenes"):
            raise ValueError("Story missing scenes")

        story = self._ensure_scene_count(story, req, system)

        with session_scope() as session:
            repo = Repository(session)
            row = repo.create_story(
                title=story.get("title", "Untitled"),
                language=req.language,
                genre=req.genre,
                target_duration_sec=req.target_duration_sec,
                is_short=req.is_short,
                story_json=story,
                lessons_applied={"lessons_snapshot": lessons},
            )
            story["story_project_id"] = row.id

        return story

    def _ensure_scene_count(
        self, story: dict[str, Any], req: StoryGenerationRequest, system: str
    ) -> dict[str, Any]:
        if req.is_short:
            return story
        min_scenes = self.settings.story_min_scenes
        scenes = story.get("scenes") or []
        if len(scenes) >= min_scenes:
            return story

        for attempt in range(3):
            scenes = story.get("scenes") or []
            if len(scenes) >= min_scenes:
                break
            needed = min_scenes - len(scenes)
            logger.info(
                "Expanding story attempt %s: %s -> need %s more scenes",
                attempt + 1,
                len(scenes),
                needed,
            )
            expand_prompt = f"""Continue this Hindi story JSON. Add at least {needed} NEW scenes.
Keep characters consistent. Language rules: Hindi Devanagari narration/dialogue; English visual_description.
Each new scene needs 5-7 Hindi sentences (~22-30s spoken), dialogue where possible, and a retention hook at the scene end.
Existing title: {story.get("title")}
Characters: {story.get("characters")}
Last scenes: {scenes[-3:]}

Return JSON:
{{"scenes": [ ... new scenes only, scene_number continues ... ]}}
"""
            response = self.llm.complete(expand_prompt, system=system, json_mode=True)
            extra = self.llm.parse_json(response.text)
            new_scenes = extra.get("scenes") or []
            if not new_scenes:
                break
            max_num = max(s.get("scene_number", i + 1) for i, s in enumerate(scenes))
            for i, sc in enumerate(new_scenes):
                sc["scene_number"] = sc.get("scene_number") or max_num + i + 1
            story["scenes"] = scenes + new_scenes
        return story
