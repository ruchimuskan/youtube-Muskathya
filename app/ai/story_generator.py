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
      "duration_estimate_sec": 40,
      "visual_description": "English cinematic image prompt for this exact moment",
      "image_prompt": "optional extra English prompt",
      "narration": "Detailed Hindi Devanagari narrative paragraph (8-12 sentences, min 400 Devanagari characters)",
      "dialogue": [{"character": "name", "line": "Hindi Devanagari dialogue", "gender": "male|female"}],
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
            "You are an ELITE Indian story creator, thriller novelist, Bollywood screenplay writer, "
            "and YouTube audience-retention expert. Your mission is to create original, emotionally powerful, "
            "unpredictable, cinematic Hindi stories that viewers cannot stop watching until the very end.\n\n"
            "ABSOLUTE RULE: NO BORING STORIES.\n"
            "NEVER generate:\n"
            "- Repeated poor girl/rich boy love stories.\n"
            "- Generic mother-son sacrifice stories.\n"
            "- Predictable village moral stories.\n"
            "- Repetitive ghost/daayan stories.\n"
            "- Stories where everything is obvious from the beginning.\n"
            "- Unnecessary descriptions and long introductory filler.\n"
            "- Artificial emotional dialogues.\n"
            "- Predictable happy endings.\n\n"
            "CORE PILLARS:\n"
            "1. COLD OPEN HOOK (First 5-10s): Start directly with a shocking, mysterious, emotional, or unexpected incident, "
            "dialogue, betrayal, impossible situation, or disturbing secret. NEVER start with boring introductions like "
            "'Ek gaon mein ek aadmi rehta tha' or weather/setting descriptions.\n"
            "2. RETENTION PACING: Introduce a new development or tension beat every 30-45 seconds. Avoid repetitive scenes. "
            "Every scene must reveal something, increase tension, or develop a character. Use natural cliffhangers at scene transitions.\n"
            "3. NATURAL HINDI DIALOGUES: Write in conversational, simple, everyday natural Hindi (Devanagari). Characters must sound "
            "like real Indian people with distinct speaking styles, emotional pauses ('...'), realistic reactions, and interruptions. "
            "Never make characters speak like formal textbook narrators. Create original dialogue suited to your characters.\n"
            "4. EMOTIONAL DEPTH & TWISTS: Every major twist must have clues planted earlier. Avoid predictable endings. The final "
            "revelation should make viewers rethink earlier scenes. Morally complicated decisions and unexpected connections over forced fairy-tale endings.\n"
            "5. NARRATION VS DIALOGUE: Write narration separately from character dialogues. Narration sets the scene context; dialogue "
            "speaks the character's exact words. Never put a character's spoken words inside the narration field (that causes double audio in TTS).\n"
            "6. AI IMAGE VISUALS: visual_description and image_prompt MUST be in English for AI image generation.\n"
            "Output valid JSON only."
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
        else:
            scene_cap = f"{min_scenes} to {max_scenes} scenes"
            brevity = (
                f"Target ~{req.target_duration_sec}s (10-15 minutes) of spoken audio across {scene_cap}. "
                "STRICT DURATION MANDATE: Total spoken story MUST have at least 7,000 Devanagari characters. "
                "Every single scene MUST have an extensive, deep, dramatic Hindi narration paragraph "
                "(MINIMUM 350-500 Devanagari characters, 8-12 sentences) "
                "PLUS 2-4 realistic dialogue exchanges between characters with emotional pauses. "
                "DO NOT write 1-2 sentence summaries or brief lines. Write vivid cinematic descriptions and gritty, realistic dialogues. "
                "Structure: cold open hook → escalating conflict → unexpected clues/twists → high tension climax → shocking ending. "
                "CRITICAL COMPLETENESS RULE: The story MUST be 100% complete — full beginning, middle, AND end. "
                "NEVER leave the story unfinished, unresolved, or abruptly cut. "
                "The final scene MUST include a clear, satisfying resolution or a powerful shocking revelation. "
                "Viewer must feel the story is fully told when it ends — no cliffhangers without resolution, no open loops."
            )

        lang_rules = ""
        if req.language == "hi":
            lang_rules = """
- Hindi Devanagari ONLY for narration, dialogue, title, synopsis, hook, ending, call_to_action
- Natural emotional Hindi, not translated English
- Pronounce-friendly sentences for TTS
- Include call_to_action field in Hindi
- CRITICAL: narration must NOT repeat or quote the dialogue lines. Narration sets the scene context; dialogue speaks the character's exact words. Never put a character's spoken words inside the narration field — that causes double audio.
- STRICT ANTI-REPETITION MANDATE: Every single scene MUST have unique, progressing narration (at least 3-5 sentences) and distinct character dialogue. NEVER repeat the same phrase, sentence, or dialogue across scenes. Each scene must advance the story with new information or conflict.
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
- ABSOLUTE RULE: NO BORING STORIES:
  * NEVER generate: repeated poor girl/rich boy love stories, generic mother-son sacrifice stories, predictable village moral stories, repetitive ghost/daayan stories, obvious endings.
  * Every new story must have a unique concept, conflict, setting, believable characters, and an unpredictable ending.
- 1. STORY OPENING (First 5-10 seconds):
  * Scene 1 MUST start directly with a shocking, mysterious, emotional, or unexpected incident, dialogue, betrayal, or impossible situation.
  * First 5-10 seconds must trigger immediate curiosity and hook the audience.
  * NEVER start with boring introductions like "Ek gaon mein ek aadmi rehta tha" or generic setting/weather descriptions.
- 2. AUDIENCE RETENTION & PACING:
  * Introduce a new development or tension beat approximately every 30-45 seconds.
  * Avoid repetitive scenes and unnecessary filler explanations.
  * Every scene must reveal new information, increase tension, or develop a character.
  * End scenes with natural cliffhangers at important transitions.
- 3. NATURAL CONVERSATIONAL HINDI DIALOGUES:
  * Conversational, simple, everyday natural Hindi (Devanagari). Characters must sound like real Indian people.
  * Give every character a distinct speaking style with emotional pauses ('...'), realistic reactions, and interruptions.
  * Avoid overly formal or textbook Hindi (BAD: "माता जी, मैं आपसे एक महत्वपूर्ण विषय पर चर्चा करना चाहता हूँ।" -> GOOD: "माँ... तुमसे एक बात कहनी थी। लेकिन समझ नहीं आ रहा कैसे बोलूँ।").
  * Do not make characters speak like narrators. Never summarize an emotional scene that should be shown through dialogue.
- 4. LOGICAL TWISTS & CLIMAX:
  * Multiple meaningful twists. Every major twist must have clues planted earlier.
  * Avoid predictable endings. The final revelation should make viewers rethink earlier scenes.
  * Prefer shocking revelations, unexpected connections, or morally complicated decisions over forced happy endings.
- 5. NARRATION AND TTS AUDIO SEPARATION:
  * Narration sets the scene context; dialogue speaks the character's exact words.
  * CRITICAL: Never put a character's spoken words inside the narration field — that causes double audio in TTS.
  * Distinct speaker labels in dialogue array with gender and Devanagari lines.
- 6. GOLDEN RULE:
  * Write stories that people WANT to finish, not stories that merely fill duration.
  * Originality, emotional connection, suspense, natural dialogue, and audience retention are paramount.
- 7. STORY COMPLETENESS (NON-NEGOTIABLE):
  * The story MUST be 100% complete — full beginning, middle, AND satisfying end.
  * NEVER stop mid-story. NEVER leave plot threads unresolved.
  * The final scene must clearly resolve the central conflict or deliver the shocking final revelation.
  * A viewer watching till the last second must feel the story is fully told — not cut off, not rushed.
  * Budget scenes properly: use early scenes for hook/setup, middle scenes for tension/twists, last 3-4 scenes for climax and resolution.
- Character visual descriptions for consistency across all scenes
- Children-safe only if genre is children
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
        story = self._ensure_narration_depth(story, req, system)

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
        min_scenes = req.min_scenes or self.settings.story_min_scenes
        # Lower the bar: accept whatever the LLM gave if it's >= min_scenes.
        # Don't demand 20+ scenes — that forces repeated expansion calls that
        # produce malformed JSON and crash the pipeline.
        scenes_needed = min_scenes
        scenes = story.get("scenes") or []
        if len(scenes) >= scenes_needed:
            return story

        for attempt in range(3):
            scenes = story.get("scenes") or []
            if len(scenes) >= scenes_needed:
                break
            needed = scenes_needed - len(scenes)
            logger.info(
                "Expanding story attempt %s: %s -> need %s more scenes",
                attempt + 1,
                len(scenes),
                needed,
            )
            expand_prompt = f"""Continue this Hindi story JSON. Add at least {needed} NEW scenes.
Keep characters consistent. Language rules: Hindi Devanagari narration/dialogue; English visual_description.
HIGH-RETENTION RULES:
- Every new scene MUST have an extensive, deep narration paragraph of 8-12 sentences (MINIMUM 400-500 Devanagari characters) plus realistic dialogue.
- Every new scene must introduce a new development or escalate tension (30-45s retention beat).
- Natural conversational Hindi dialogue (real Indian phrasing, emotional pauses '...', no textbook formality).
- Narration sets scene context; dialogue carries spoken lines (never quote dialogue inside narration).
- End each scene with a suspense hook or emotional turn towards the climax.
Existing title: {story.get("title")}
Characters: {story.get("characters")}
Last scenes: {scenes[-3:]}

Return JSON:
{{"scenes": [ ... new scenes only, scene_number continues ... ]}}
"""
            try:
                response = self.llm.complete(expand_prompt, system=system, json_mode=True)
                extra = self.llm.parse_json(response.text)
                new_scenes = extra.get("scenes") or []
                # Deduplicate: do not accept scenes that repeat existing narration or dialogue
                existing_narrs = {s.get("narration", "").strip() for s in scenes}
                unique_new = []
                for sc in new_scenes:
                    narr = sc.get("narration", "").strip()
                    if narr and narr in existing_narrs:
                        continue
                    if narr:
                        existing_narrs.add(narr)
                    unique_new.append(sc)
                new_scenes = unique_new

                if not new_scenes:
                    logger.warning("Scene expansion attempt %s returned no unique scenes", attempt + 1)
                    break
                max_num = max(s.get("scene_number", i + 1) for i, s in enumerate(scenes))
                for i, sc in enumerate(new_scenes):
                    sc["scene_number"] = sc.get("scene_number") or max_num + i + 1
                story["scenes"] = scenes + new_scenes
            except Exception as exc:
                logger.warning(
                    "Scene expansion attempt %s failed (JSON parse): %s — continuing with %s scenes",
                    attempt + 1,
                    exc,
                    len(scenes),
                )
                # Don't crash — use whatever scenes we already have.
                break

        # Final guard: if we still don't have enough scenes, proceed anyway.
        # A shorter video is better than no video at all.
        final_count = len(story.get("scenes") or [])
        if final_count < scenes_needed:
            logger.warning(
                "Story has %s scenes (wanted %s) — proceeding with shorter video",
                final_count,
                scenes_needed,
            )
        return story

    def _calculate_spoken_chars(self, story: dict[str, Any]) -> int:
        total = 0
        for sc in story.get("scenes") or []:
            total += len(sc.get("narration", "").strip())
            for d in sc.get("dialogue") or []:
                total += len(d.get("line", "").strip())
        return total

    def _ensure_narration_depth(
        self, story: dict[str, Any], req: StoryGenerationRequest, system: str
    ) -> dict[str, Any]:
        if req.is_short:
            return story

        min_chars = max(6500, int(req.target_duration_sec * 11.5))
        scenes = story.get("scenes") or []
        current_chars = self._calculate_spoken_chars(story)
        logger.info(
            "Checking story narration depth: %d chars (required min: %d chars for 10+ min video)",
            current_chars,
            min_chars,
        )

        if current_chars >= min_chars:
            return story

        logger.info(
            "Story narration too short (%d < %d chars). Expanding scene narrations to reach 10+ min duration...",
            current_chars,
            min_chars,
        )

        import json
        batch_size = 4
        for i in range(0, len(scenes), batch_size):
            batch = scenes[i : i + batch_size]
            needs_expansion = [s for s in batch if len(s.get("narration", "").strip()) < 380]
            if not needs_expansion:
                continue

            prompt = f"""You are an elite Indian thriller and drama screenwriter.
The scenes below from Hindi story '{story.get("title")}' are currently too short.
Expand each scene's narration into a rich, detailed, dramatic Hindi Devanagari narrative paragraph of 8-12 sentences (MINIMUM 450 Devanagari characters) with intense atmosphere, character thoughts, and suspense.
Also provide 2-4 lines of natural, realistic Hindi dialogue for each scene.
Do NOT summarize. Write vivid, complete story prose.

Scenes to expand:
{json.dumps([{'scene_number': s.get('scene_number'), 'current_narration': s.get('narration'), 'current_dialogue': s.get('dialogue')} for s in needs_expansion], ensure_ascii=False, indent=2)}

Return JSON:
{{
  "expanded_scenes": [
    {{
      "scene_number": <int>,
      "narration": "Rich detailed Devanagari narrative paragraph (min 450 characters)...",
      "dialogue": [ {{"character": "name", "line": "Hindi Devanagari dialogue", "gender": "male|female"}} ]
    }}
  ]
}}
"""
            try:
                res = self.llm.complete(prompt, system=system, json_mode=True)
                data = self.llm.parse_json(res.text)
                expanded = {s.get("scene_number"): s for s in data.get("expanded_scenes", [])}
                for sc in needs_expansion:
                    sn = sc.get("scene_number")
                    if sn in expanded:
                        new_narr = expanded[sn].get("narration", "").strip()
                        if len(new_narr) > len(sc.get("narration", "")):
                            sc["narration"] = new_narr
                        new_dial = expanded[sn].get("dialogue")
                        if new_dial and isinstance(new_dial, list) and len(new_dial) > 0:
                            sc["dialogue"] = new_dial
            except Exception as exc:
                logger.warning("Failed to expand batch %s-%s: %s", i, i + batch_size, exc)

        new_total = self._calculate_spoken_chars(story)
        logger.info("After expansion, story speech chars: %d (was %d)", new_total, current_chars)
        return story
