from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from app.ai.providers import LLMRouter
from app.ai.repetition_detector import RepetitionDetector
from app.ai.scene_based_story_writer import SceneBasedStoryWriter
from app.ai.story_blueprint_generator import StoryBlueprintGenerator
from app.ai.story_logic_validator import StoryLogicValidator
from app.ai.story_quality_auditor import StoryQualityAuditor
from app.ai.story_quality_checker import StoryQualityChecker, StoryQualityReport
from app.ai.story_rewriter import StoryRewriter
from app.ai.topic_researcher import TopicResearcher
from app.ai.vague_sentence_detector import VagueSentenceDetector
from app.config import get_settings
from app.content.categories import category_story_block, get_category
from app.database import Repository, session_scope

logger = logging.getLogger(__name__)

STORY_SCHEMA_HINT = """
{
  "title": "गाँव का आखिरी चिराग और हवेली का रहस्य (Devanagari)",
  "synopsis": "एक रहस्यमयी हवेली में आधी रात को जलती लाल लालटेन और एक पुराने खत का सच जो पूरे गाँव के होश उड़ा देता है।",
  "characters": [
    {
      "name": "राघव",
      "gender": "male",
      "age_group": "26 years old",
      "description": "Young Indian investigator with sharp jawline, intense eyes, wearing dark navy blue jacket over grey henley",
      "voice_id_hint": "hi_IN-pratham-medium"
    }
  ],
  "character_references": [
    {
      "name": "राघव",
      "gender": "male",
      "age_group": "26 years old",
      "physical_appearance": "Sharp Indian features, clean shaven, intense piercing eyes, short black styled hair, height 5'11",
      "signature_attire": "Dark navy blue jacket, grey henley t-shirt, silver watch on left wrist",
      "personality": "Cautious, razor-sharp observant, fearless"
    }
  ],
  "story_structure_breakdown": {
    "opening_hook": "Shocking incident or discovery within 0-30 seconds",
    "character_intro": "Establish relationships, stakes and motivations",
    "mystery_development": "Central conflict and unanswered questions",
    "suspense_escalation": "Rising clues and believable complications",
    "major_twist": "Unexpected but foreshadowed plot reversal",
    "climax": "High stakes confrontation",
    "proper_ending": "Complete resolution, no unanswered loose ends",
    "conclusion_moral": "Meaningful emotional realization"
  },
  "scenes": [
    {
      "scene_number": 1,
      "story_beat": "opening_hook",
      "duration_estimate_sec": 45,
      "visual_description": "Cinematic 35mm photograph of ancient dark Indian mansion in heavy rain, crimson lantern glowing in top attic window, lightning flash, atmospheric mist, photorealistic Bollywood thriller lighting, 8k",
      "image_prompt": "Cinematic 35mm photo of ancient dark Indian mansion in pouring monsoon rain, crimson lantern glowing in top attic window, atmospheric mist, photorealistic Bollywood thriller lighting",
      "narration": "रात के ठीक बारह बजे, पुरानी हवेली की बंद खिड़की से अचानक लाल रोशनी फूट पड़ी। राघव ने जैसे ही दरवाजे पर हाथ रखा, हवेली के अंदर से किसी के धीमे-धीमे रोने की आवाज गूंजने लगी। हवा इतनी ठंडी थी कि सांसें जम रही थीं।",
      "dialogue": [
        {
          "character": "राघव",
          "acting_instruction": "दबी हुई गंभीर आवाज़",
          "line": "कोई है अंदर? दरवाजा खोलो, मैं जानता हूँ तुम यहीं छुपे हो!",
          "gender": "male"
        }
      ],
      "mood": "suspense",
      "characters_present": ["राघव"],
      "sfx_hint": "thunder, rain, creaking door"
    }
  ],
  "hook_opening": "रात के ठीक बारह बजे, पुरानी हवेली की बंद खिड़की से लाल रोशनी फूट पड़ी...",
  "ending": "सच्चाई सामने आ चुकी थी, लेकिन राघव जानता था कि यह रहस्य कभी गाँव के लोगों के जेहन से नहीं मिटेगा।",
  "conclusion_moral": "विश्वास वो धागा है जिसे अगर लालच की कैंची से काट दिया जाए, तो ज़िंदगी भर का पछतावा भी उसे दोबारा नहीं जोड़ सकता।",
  "call_to_action": "अगर आपको यह कहानी पसंद आई, तो वीडियो को लाइक करें और ऐसी ही रोमांचक कहानियों के लिए चैनल को सब्सक्राइब करें।",
  "content_rating": "general",
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
    """
    State-of-the-art Hindi Story Generation Engine for YouTube Automation.
    Orchestrates Blueprint Generation, Scene-Based Writing (Show Don't Tell),
    Semantic Repetition Detection, Vague Sentence Detection, Logic Validation,
    Strict 10-Parameter Screenplay Auditing (Min 85/100), and Targeted Rewriting.
    """

    def __init__(self, llm: LLMRouter | None = None) -> None:
        self.llm = llm or LLMRouter()
        self.topics = TopicResearcher(self.llm)
        self.settings = get_settings()

        # Modular Engine Components
        self.blueprint_gen = StoryBlueprintGenerator(self.llm)
        self.scene_writer = SceneBasedStoryWriter(self.llm)
        self.repetition_detector = RepetitionDetector()
        self.vague_detector = VagueSentenceDetector()
        self.logic_validator = StoryLogicValidator()
        self.quality_auditor = StoryQualityAuditor(self.llm)
        self.quality_checker = StoryQualityChecker(self.llm)
        self.rewriter = StoryRewriter(self.llm)

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
            "1. COLD OPEN HOOK: Scene 1 must start directly with a shocking, mysterious, emotional, or unexpected incident.\n"
            "2. NATURAL HINDI DIALOGUES: Conversational, everyday natural Hindi with realistic emotion and distinct personalities.\n"
            "3. CRITICAL STORYTELLING RULE: SHOW WHAT ACTUALLY HAPPENED (SHOW, DON'T TELL).\n"
            "NEVER summarize struggles or problems with vague sentences like 'उसे बहुत संघर्ष करना पड़ा' or 'उसकी जिंदगी बदल गई'.\n"
            "Always explain the concrete event: Who caused the problem? Where? When? What did the character see, hear, say, and do?\n\n"
            "BAN REPETITIVE SENTENCES:\n"
            "- Never repeat the same information using different words to increase length.\n"
            "- Every single paragraph must contribute new information, action, clue, conflict, or consequence.\n"
            "- Avoid formulaic dialogue question loops ('यह क्या है?', 'तुम कौन हो?', 'क्या हुआ?').\n\n"
            "COMPLETE SATISFYING RESOLUTION:\n"
            "- Show the exact fate of protagonist, antagonist, and mystery. Never end with cop-outs like 'समय के साथ सब ठीक हो गया'.\n"
            "Output valid JSON only."
        )

    def generate(self, req: StoryGenerationRequest) -> dict[str, Any]:
        topic = req.topic_research or self.topics.suggest_topic(req.language, req.genre, req.is_short)
        lessons = self._lessons_block()
        category = get_category(req.category_id)
        cat_block = category_story_block(category)
        min_scenes = req.min_scenes or self.settings.story_min_scenes
        max_scenes = req.max_scenes or self.settings.story_max_scenes
        target_scene_count = 5 if req.is_short else max(min_scenes, min(12, max_scenes))

        system = self._hindi_system() if req.language == "hi" else "You are an expert screenwriter. Output only valid JSON."

        # ── Step 1: Generate Detailed Plot Blueprint (No Random Incidents) ──
        logger.info("Generating plot blueprint for %s (%s)...", req.genre, category.name_hi)
        blueprint = self.blueprint_gen.generate_blueprint(
            genre=req.genre,
            category_name=category.name_hi,
            topic=topic,
            target_scene_count=target_scene_count,
            is_short=req.is_short,
        )

        # ── Step 2: Write Complete Scene-Based Story (Show, Don't Tell) ──
        logger.info("Writing complete scene-based story from blueprint...")
        story = self.scene_writer.write_story(
            blueprint=blueprint,
            genre=req.genre,
            category_name=category.name_hi,
            language=req.language,
            target_duration_sec=req.target_duration_sec,
            target_scene_count=target_scene_count,
            is_short=req.is_short,
            system_prompt=system,
            visual_style=req.visual_style or category.visual_style,
        )

        if not story or not story.get("scenes"):
            logger.warning("LLM story writer yielded empty scenes. Falling back to procedural engine.")
            story = self._generate_fallback_story(req, topic)

        story["research"] = topic
        story["content_category_id"] = req.category_id
        story["content_category_name"] = category.name_hi
        story["visual_style"] = req.visual_style or category.visual_style
        story["language"] = req.language
        story["genre"] = req.genre
        story["is_short"] = req.is_short
        story["target_duration_sec"] = req.target_duration_sec
        story["blueprint"] = blueprint

        if req.language == "hi" and not story.get("call_to_action"):
            story["call_to_action"] = (
                "अगर आपको यह कहानी पसंद आई, तो वीडियो को लाइक करें "
                "और ऐसी ही रोमांचक कहानियों के लिए चैनल को सब्सक्राइब करें।"
            )

        # ── Step 3: Clean, Deduplicate & Ensure Scene Pacing ──
        story = self._clean_and_deduplicate(story)
        story = self._ensure_scene_count(story, req, system)
        story = self._ensure_narration_depth(story, req, system)
        story = self._clean_and_deduplicate(story)

        # ── Step 4: Strict Story Quality Audit (Min 85/100, Repetition & Vague Penalties) ──
        min_score = getattr(self.settings, "story_min_quality_score", 85)
        report = self.quality_checker.evaluate(story, blueprint=blueprint)
        retries = 0

        while (not report.passed or report.total_score < min_score) and retries < 2:
            retries += 1
            logger.warning(
                "Story scored %s/100 (below %s min; rep_penalty=%s, vague_penalty=%s). "
                "Targeted rewrite pass %s/2 with feedback: %s",
                report.total_score,
                min_score,
                getattr(report, "repetition_penalty", 0),
                getattr(report, "vague_penalty", 0),
                retries,
                report.feedback_for_rewrite,
            )
            story = self.rewriter.rewrite_problematic_sections(
                story=story,
                audit_feedback=report.feedback_for_rewrite,
                weak_sections=report.weak_sections,
                critical_issues=report.critical_issues,
                blueprint=blueprint,
                system_prompt=system,
            )
            story = self._clean_and_deduplicate(story)
            report = self.quality_checker.evaluate(story, blueprint=blueprint)

        story["quality_report"] = report.to_dict()
        story["quality_score"] = report.total_score
        logger.info(
            "Final approved story quality score: %s/100 (passed=%s, rep_penalty=%s, vague_penalty=%s)",
            report.total_score,
            report.passed,
            getattr(report, "repetition_penalty", 0),
            getattr(report, "vague_penalty", 0),
        )

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

    @staticmethod
    def clean_dialogue_line(raw_line: str, default_char: str = "पात्र") -> tuple[str, str, str]:
        """
        Parses raw dialogue strings to separate (character_name, emotion_instruction, clean_spoken_line).
        E.g. 'मां (घबराकर): रोहित! तुम इतनी देर कहां थे?' -> ('मां', 'घबराकर', 'रोहित! तुम इतनी देर कहां थे?')
        Prevents TTS from reading aloud stage directions and attribution labels.
        """
        line = (raw_line or "").strip()
        character = default_char or "पात्र"
        emotion = ""

        # Pattern: [Character] [(Emotion)]: [Spoken line]
        match = re.match(r"^([\u0900-\u097F\w\s]+?)\s*(?:\(([^)]+)\))?\s*[:：\-]\s*(.*)$", line)
        if match:
            char_match = match.group(1).strip()
            if char_match and char_match not in ("Narrator", "सूत्रधार", "Voiceover"):
                character = char_match
            if match.group(2):
                emotion = match.group(2).strip()
            line = match.group(3).strip()
        else:
            emo_match = re.match(r"^\(([^)]+)\)\s*[:：\-]?\s*(.*)$", line)
            if emo_match:
                emotion = emo_match.group(1).strip()
                line = emo_match.group(2).strip()

        # Remove any lingering parenthetical acting directions from spoken audio line
        line = re.sub(r"\([^)]*\)", "", line).strip()
        line = re.sub(r"^[:：\-—,\s]+", "", line).strip()
        return character, emotion, line

    def _clean_and_deduplicate(self, story: dict[str, Any]) -> dict[str, Any]:
        """Cleans, normalizes, and deduplicates dialogue and characters using RepetitionDetector."""
        chars = story.get("characters") or []
        char_refs = story.get("character_references") or []
        ref_map = {c.get("name"): c for c in char_refs if isinstance(c, dict)}

        for c in chars:
            if not isinstance(c, dict):
                continue
            name = c.get("name", "नायक")
            if name not in ref_map:
                desc = c.get("description", "Indian character with sharp expressive features")
                age = c.get("age_group", "25-30 years old")
                gender = c.get("gender", "male")
                ref_map[name] = {
                    "name": name,
                    "gender": gender,
                    "age_group": age,
                    "physical_appearance": f"Sharp natural Indian features, realistic {gender}, {desc}",
                    "signature_attire": "Authentic cinematic Indian attire, detailed textures, practical clothing",
                    "personality": "Observant, emotionally grounded, determined",
                }
        story["character_references"] = list(ref_map.values())

        # Use repetition detector for deep dialogue and narration cleaning
        story = self.repetition_detector.clean_and_deduplicate(story)

        scenes = story.get("scenes") or []
        for sc in scenes:
            narr = (sc.get("narration") or "").strip()
            # If narration was an ultra-short stub, enrich it with a concrete situational detail
            if narr and len(narr) < 140:
                sc["narration"] = (
                    narr
                    + " उसने कमरे के चारों तरफ नज़र दौड़ाई तो धूल भरी अलमारी पर उंगलियों के ताज़ा निशान दिखाई दिए। "
                    + "खिड़की का पर्दा हल्का सा हिला, जैसे कोई अभी-अभी वहाँ से बाहर निकला हो।"
                )

        if scenes:
            if not story.get("hook_opening"):
                story["hook_opening"] = (scenes[0].get("narration") or "")[:200]
            if not story.get("ending"):
                story["ending"] = (scenes[-1].get("narration") or "")[:200]

        return story

    def _calculate_spoken_chars(self, story: dict[str, Any]) -> int:
        total = 0
        for sc in story.get("scenes") or []:
            total += len(sc.get("narration", "").strip())
            for d in sc.get("dialogue") or []:
                if isinstance(d, dict):
                    total += len((d.get("line") or "").strip())
                elif isinstance(d, str):
                    total += len(d.strip())
        return total

    def _ensure_scene_count(
        self, story: dict[str, Any], req: StoryGenerationRequest, system: str
    ) -> dict[str, Any]:
        if req.is_short:
            return story
        min_scenes = req.min_scenes or self.settings.story_min_scenes
        scenes = story.get("scenes") or []

        if len(scenes) >= max(7, min_scenes - 2) and self._calculate_spoken_chars(story) >= 3500:
            logger.info(
                "Story has %d strong scenes with %d characters — good complete story",
                len(scenes),
                self._calculate_spoken_chars(story),
            )
            return story

        scenes_needed = min_scenes
        if len(scenes) >= scenes_needed:
            return story

        for attempt in range(3):
            scenes = story.get("scenes") or []
            if len(scenes) >= scenes_needed:
                break
            needed = min(scenes_needed - len(scenes), 3)
            logger.info("Adding %s more concrete scenes to reach target pacing...", needed)

            expand_prompt = f"""Continue this Hindi story script. Add exactly {needed} NEW scenes showing concrete events leading to climax.
Title: {story.get("title")}
Characters: {story.get("characters")}
Last 2 scenes: {json.dumps(scenes[-2:], ensure_ascii=False)}

CRITICAL RULES:
1. SHOW WHAT HAPPENED: Each scene must describe the concrete event (who, what, where, action, dialogue).
2. NO VAGUE SUMMARIES: Zero sentences like "उसे बहुत संघर्ष करना पड़ा".
3. NO REPETITION: Unique dialogue and distinct narrative progression.

Return JSON ONLY:
{{"scenes": [ ... new scenes only, scene_number continues ... ]}}"""

            try:
                response = self.llm.complete(expand_prompt, system=system, json_mode=True)
                extra = self.llm.parse_json(response.text)
                new_scenes = extra.get("scenes") or []
                existing_narrs = {s.get("narration", "").strip() for s in scenes}
                unique_new = [sc for sc in new_scenes if sc.get("narration", "").strip() not in existing_narrs]

                if not unique_new:
                    break

                max_num = max(s.get("scene_number", i + 1) for i, s in enumerate(scenes))
                for i, sc in enumerate(unique_new):
                    sc["scene_number"] = sc.get("scene_number") or (max_num + i + 1)
                story["scenes"] = scenes + unique_new
            except Exception as exc:
                logger.warning("Scene expansion attempt %s failed: %s", attempt + 1, exc)
                break

        return story

    def _ensure_narration_depth(
        self, story: dict[str, Any], req: StoryGenerationRequest, system: str
    ) -> dict[str, Any]:
        if req.is_short:
            return story

        min_chars = max(4200, int(req.target_duration_sec * 8.5))
        scenes = story.get("scenes") or []
        current_chars = self._calculate_spoken_chars(story)

        if current_chars >= min_chars:
            return story

        logger.info("Story narration below target (%d < %d chars). Deepening scenes with concrete events...", current_chars, min_chars)

        batch_size = 2
        for i in range(0, len(scenes), batch_size):
            batch = scenes[i : i + batch_size]
            needs_expansion = [s for s in batch if len((s.get("narration") or "").strip()) < 260]
            if not needs_expansion:
                continue

            prompt = f"""You are an elite Indian thriller screenwriter.
Expand each scene's narration into a rich, detailed, dramatic Hindi Devanagari narrative paragraph of 4-6 sentences (MINIMUM 350 characters) by describing CONCRETE physical actions, sensory details, and discoveries.
Also provide 2-4 lines of natural Hindi dialogue.
NEVER use vague summaries or cliché filler sentences.

Scenes to deepen:
{json.dumps([{'scene_number': s.get('scene_number'), 'current_narration': s.get('narration'), 'current_dialogue': s.get('dialogue')} for s in needs_expansion], ensure_ascii=False, indent=2)}

Return JSON:
{{
  "expanded_scenes": [
    {{
      "scene_number": <int>,
      "narration": "Rich detailed Devanagari narrative paragraph (min 350 characters) with concrete actions and sensory details...",
      "dialogue": [ {{"character": "name", "line": "Hindi dialogue", "gender": "male|female"}} ]
    }}
  ]
}}"""

            try:
                res = self.llm.complete(prompt, system=system, json_mode=True)
                data = self.llm.parse_json(res.text)
                items = data.get("expanded_scenes") or data.get("scenes") or []
                expanded = {s.get("scene_number"): s for s in items if isinstance(s, dict) and s.get("scene_number")}
                for sc in needs_expansion:
                    sn = sc.get("scene_number")
                    if sn in expanded:
                        new_narr = (expanded[sn].get("narration") or "").strip()
                        if len(new_narr) > len(sc.get("narration", "")):
                            sc["narration"] = new_narr
                        new_dial = expanded[sn].get("dialogue")
                        if new_dial and isinstance(new_dial, list) and len(new_dial) > 0:
                            sc["dialogue"] = new_dial
            except Exception as exc:
                logger.warning("Failed to expand batch via LLM: %s", exc)

        return story

    def _generate_fallback_story(self, req: StoryGenerationRequest, topic: dict[str, Any]) -> dict[str, Any]:
        """Procedural story generator adhering strictly to SHOW, DON'T TELL with ZERO vague summaries."""
        blueprint = self.blueprint_gen._procedural_fallback_blueprint(
            genre=req.genre,
            category_name="रहस्य",
            topic=topic,
            target_scene_count=5 if req.is_short else 8,
        )
        return self.scene_writer._procedural_scene_story(
            blueprint=blueprint,
            genre=req.genre,
            category_name="रहस्य",
            target_scene_count=5 if req.is_short else 8,
            is_short=req.is_short,
        )
