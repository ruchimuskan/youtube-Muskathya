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
  "title": "गाँव का आखिरी चिराग और हवेली का रहस्य (Devanagari)",
  "synopsis": "एक रहस्यमयी हवेली में आधी रात को जलती लाल लालटेन और एक पुराने खत का सच जो पूरे गाँव के होश उड़ा देता है।",
  "characters": [
    {"name": "राघव", "gender": "male", "age_group": "young adult", "description": "Indian youth with leather jacket and flashlight, intense eyes", "voice_id_hint": "hi_IN-pratham-medium"}
  ],
  "character_references": [
    {"name": "राघव", "gender": "male", "age_group": "young adult", "description": "Indian youth with leather jacket and flashlight, intense eyes"}
  ],
  "scenes": [
    {
      "scene_number": 1,
      "story_beat": "hook",
      "duration_estimate_sec": 45,
      "visual_description": "A dark spooky Indian mansion in heavy rain, mysterious red lantern shining in top window, cinematic lighting, 8k",
      "image_prompt": "A dark spooky Indian mansion in heavy rain, mysterious red lantern shining in top window, cinematic lighting, 8k",
      "narration": "रात के ठीक बारह बजे, पुरानी हवेली की बंद खिड़की से अचानक लाल रोशनी फूट पड़ी। राघव ने जैसे ही दरवाजे पर हाथ रखा, हवेली के अंदर से किसी के धीमे-धीमे रोने की आवाज गूंजने लगी। हवा इतनी ठंडी थी कि सांसें जम रही थीं।",
      "dialogue": [{"character": "राघव", "line": "कोई है अंदर? दरवाजा खोलो, मैं जानता हूँ तुम यहीं छुपे हो!", "gender": "male"}],
      "mood": "suspense",
      "sfx_hint": "thunder, rain, creaking door"
    }
  ],
  "hook_opening": "रात के ठीक बारह बजे, पुरानी हवेली की बंद खिड़की से लाल रोशनी फूट पड़ी...",
  "ending": "सच्चाई सामने आ चुकी थी, लेकिन राघव जानता था कि यह रहस्य कभी गाँव के लोगों के जेहन से नहीं मिटेगा।",
  "call_to_action": "अगर आपको यह कहानी पसंद आई, तो वीडियो को लाइक करें और ऐसी ही कहानियों के लिए चैनल को सब्सक्राइब करें।",
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
            "STRICT ANTI-REPETITION MANDATE:\n"
            "- NEVER use formulaic, repetitive scene structures where a character simply walks into rooms, finds random objects, and acts surprised.\n"
            "- NEVER repeat the same questions or dialogue across scenes like 'यह क्या है?', 'यह क्या हो रहा है?', 'तुम कौन हो?', 'यह क्या मतलब है?', 'तुम्हें कुछ नहीं पता'. Each line of dialogue must be distinct, emotionally meaningful, and advance the plot.\n"
            "- NEVER write 1-2 sentence stub narrations. Every single scene must have a rich, atmospheric paragraph of 4-7 descriptive sentences (300-500 Devanagari characters) with vivid sensory details, character psychology, and tension.\n\n"
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
            scene_cap = f"exactly {min_scenes} to {max_scenes} scenes"
            brevity = (
                f"Generate a deep, engaging, complete cinematic Hindi story of {scene_cap}. "
                "CRITICAL STORYTELLING RULES: "
                "1. NO 1-2 SENTENCE SUMMARIES. Every scene MUST have a rich narrative paragraph (4-7 detailed sentences, MINIMUM 300-450 Devanagari characters) with atmosphere, sensory details, and emotional tension. "
                "2. AUTHENTIC DIALOGUE: Every scene MUST have 2-4 lines of natural Hindi dialogue between characters with emotion, pauses ('...'), and distinct personalities. "
                "3. ABSOLUTE ANTI-REPETITION: NEVER repeat questions like 'यह क्या है?', 'यह क्या हो रहा है?', 'तुम कौन हो?'. Every dialogue line must be unique and directly tied to the scene's events. "
                "4. COMPLETE 3-ACT STRUCTURE: "
                "   - Scene 1: Cold hook with high curiosity and immediate tension. "
                "   - Early scenes: Background, characters, first clue / complication. "
                "   - Middle scenes: Rising stakes, false leads, dark discoveries, emotional confrontations. "
                "   - Climax scenes: Shocking confrontation, unexpected twist that reframes earlier clues. "
                "   - Final scene: Full, satisfying resolution that leaves the viewer spellbound. "
                "5. The entire story MUST be fully self-contained, resolving all questions."
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
            try:
                response = self.llm.complete(
                    prompt + extra,
                    system=system,
                    json_mode=True,
                )
                story = self.llm.parse_json(response.text)
                break
            except Exception as exc:
                last_err = exc
                logger.warning("Story generation attempt %s failed: %s", attempt + 1, exc)
        if story is None:
            logger.warning("LLM story generation failed (%s). Using procedural storytelling engine.", last_err)
            story = self._generate_fallback_story(req, topic)

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

        story = self._clean_and_deduplicate(story)
        story = self._ensure_scene_count(story, req, system)
        story = self._ensure_narration_depth(story, req, system)
        story = self._clean_and_deduplicate(story)

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

    GENERIC_REPETITIVE_DIALOGUES = {
        "यह क्या है",
        "यह क्या हो रहा है",
        "तुम कौन हो",
        "यह कौन है",
        "यह क्या मतलब है",
        "तुम्हें कुछ नहीं पता",
        "मैं जानता हूँ कि आप कौन हैं",
        "मैं जानता हूं कि आप कौन हैं",
        "यह कैसे संभव है",
        "मैं समझ गया हूँ",
        "मैं समझ गया हूं",
        "मुझे इसके बारे में पता चलना चाहिए",
        "मुझे यह चाबी मिलनी चाहिए",
        "मैं अकेला नहीं हूँ",
        "मैं अकेला नहीं हूं",
        "मुझे यहाँ से निकलना होगा",
        "मुझे यहां से निकलना होगा",
        "कौन है",
        "क्या हुआ",
    }

    DYNAMIC_DIALOGUE_POOL = [
        "मुझे यकीन नहीं हो रहा... यह सच यहाँ कैसे छुपा हो सकता है?",
        "इस खौफ़नाक मंज़र के पीछे कोई बहुत बड़ा राज़ छुपा है।",
        "अगर यह बात सच है, तो हम सबकी जान भारी खतरे में है।",
        "तुम मुझसे कुछ छुपा रहे हो... साफ़-साफ़ बताओ आखिर हुआ क्या था!",
        "अब पीछे हटने का कोई रास्ता नहीं बचा, सच्चाई सामने लाकर ही रहेंगे।",
        "यह सब कोई सोची-समझी साज़िश है... मुझे हर हाल में तह तक पहुँचना होगा।",
        "रुको... तुमने इस निशान पर गौर किया? यहाँ कुछ तो बेहद भयानक घटा है।",
        "अगर हमने तुरंत सच नहीं ढूँढा, तो बहुत देर हो जाएगी।",
        "इस जगह की खामोशी में कोई गहरा खौफ़ दफ़न है...",
        "मुझे लगा था कि सब कुछ सुलझ गया है, लेकिन यह तो बस एक शुरुआत थी...",
    ]

    def _clean_and_deduplicate(self, story: dict[str, Any]) -> dict[str, Any]:
        scenes = story.get("scenes") or []
        seen_dialogues: set[str] = set()
        pool_idx = 0

        for sc in scenes:
            sn = sc.get("scene_number", 1)
            narr = (sc.get("narration") or "").strip()

            # Ensure minimum narration substance
            if narr and len(narr) < 140:
                mood = (sc.get("mood") or "suspense").lower()
                if "suspense" in mood or "horror" in mood:
                    narr += (
                        " चारों तरफ गहरा सन्नाटा पसरा हुआ था और दिल की धड़कनें साफ़ सुनाई दे रही थीं। "
                        "हवा का हर झोंका किसी अनहोनी का इशारा दे रहा था।"
                    )
                else:
                    narr += (
                        " माहौल में एक अजीब सी बेचैनी थी और हर गुज़रते पल के साथ "
                        "सवालों की उलझन और भी गहरी होती जा रही थी।"
                    )
                sc["narration"] = narr

            # Deduplicate dialogue lines
            new_dialogue = []
            for d in sc.get("dialogue") or []:
                if isinstance(d, str):
                    d = {"character": "पात्र", "line": d, "gender": "male"}
                elif not isinstance(d, dict):
                    continue
                line = (d.get("line") or "").strip()
                if not line:
                    continue
                norm = line.replace("?", "").replace("।", "").replace("!", "").replace(".", "").replace(",", "").strip()

                is_duplicate = norm in seen_dialogues

                if is_duplicate:
                    # Replace with unique, situation-grounded dialogue
                    replacement = self.DYNAMIC_DIALOGUE_POOL[pool_idx % len(self.DYNAMIC_DIALOGUE_POOL)]
                    pool_idx += 1
                    logger.info("Scene %s: Replaced repetitive dialogue '%s' -> '%s'", sn, line, replacement)
                    d["line"] = replacement
                    seen_dialogues.add(replacement)
                else:
                    seen_dialogues.add(norm)
                new_dialogue.append(d)
            sc["dialogue"] = new_dialogue

        return story

    def _ensure_scene_count(
        self, story: dict[str, Any], req: StoryGenerationRequest, system: str
    ) -> dict[str, Any]:
        if req.is_short:
            return story
        min_scenes = req.min_scenes or self.settings.story_min_scenes
        scenes = story.get("scenes") or []

        # If we have at least 7 scenes and solid speech length, do NOT append zombie scenes!
        if len(scenes) >= max(7, min_scenes - 2) and self._calculate_spoken_chars(story) >= 3500:
            logger.info("Story has %d strong scenes with %d characters — good complete story", len(scenes), self._calculate_spoken_chars(story))
            return story

        scenes_needed = min_scenes
        if len(scenes) >= scenes_needed:
            return story

        for attempt in range(4):
            scenes = story.get("scenes") or []
            if len(scenes) >= scenes_needed:
                break
            needed = min(scenes_needed - len(scenes), 3)
            logger.info(
                "Expanding story attempt %s: currently %s scenes -> adding %s more scenes",
                attempt + 1,
                len(scenes),
                needed,
            )
            expand_prompt = f"""Continue this Hindi story JSON. Add exactly {needed} NEW scenes to progress the plot towards climax and resolution.
Title: {story.get("title")}
Synopsis: {story.get("synopsis")}
Characters: {story.get("characters")}
Current scenes outline: {[s.get("story_beat", "") + ": " + s.get("narration", "")[:60] for s in scenes]}
Last scenes: {scenes[-2:]}

HIGH-RETENTION RULES:
- Every new scene MUST have an extensive narration paragraph (MINIMUM 300 Devanagari characters, 4-6 sentences) plus realistic dialogue.
- Natural conversational Hindi dialogue (real Indian phrasing, emotional pauses '...', no textbook formality).
- Narration sets scene context; dialogue carries spoken lines (never quote dialogue inside narration).
- End each scene with a suspense hook or emotional turn towards the climax.
- NEVER repeat generic questions like 'यह क्या है?', 'यह क्या हो रहा है?'.

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
                    "Scene expansion attempt %s failed: %s — continuing with %s scenes",
                    attempt + 1,
                    exc,
                    len(scenes),
                )
                break

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

        min_chars = max(4200, int(req.target_duration_sec * 8.5))
        scenes = story.get("scenes") or []
        current_chars = self._calculate_spoken_chars(story)
        logger.info(
            "Checking story narration depth: %d chars (required min: %d chars for long video)",
            current_chars,
            min_chars,
        )

        if current_chars >= min_chars:
            return story

        logger.info(
            "Story narration below target (%d < %d chars). Deepening scenes...",
            current_chars,
            min_chars,
        )

        import json
        batch_size = 2
        for i in range(0, len(scenes), batch_size):
            batch = scenes[i : i + batch_size]
            needs_expansion = [s for s in batch if len(s.get("narration", "").strip()) < 260]
            if not needs_expansion:
                continue

            prompt = f"""You are an elite Indian thriller and drama screenwriter.
The scenes below from Hindi story '{story.get("title")}' are currently too short.
Expand each scene's narration into a rich, detailed, dramatic Hindi Devanagari narrative paragraph of 5-8 sentences (MINIMUM 350 Devanagari characters) with intense atmosphere, character thoughts, and suspense.
Also provide 2-4 lines of natural, realistic Hindi dialogue for each scene.
Do NOT summarize. Write vivid, complete story prose.
NEVER repeat generic questions like 'यह क्या है?' or 'यह क्या हो रहा है?'.

Scenes to expand:
{json.dumps([{'scene_number': s.get('scene_number'), 'current_narration': s.get('narration'), 'current_dialogue': s.get('dialogue')} for s in needs_expansion], ensure_ascii=False, indent=2)}

Return JSON:
{{
  "expanded_scenes": [
    {{
      "scene_number": <int>,
      "narration": "Rich detailed Devanagari narrative paragraph (min 350 characters)...",
      "dialogue": [ {{"character": "name", "line": "Hindi Devanagari dialogue", "gender": "male|female"}} ]
    }}
  ]
}}
"""
            try:
                res = self.llm.complete(prompt, system=system, json_mode=True)
                data = self.llm.parse_json(res.text)
                items = data.get("expanded_scenes") or data.get("scenes") or []
                expanded = {s.get("scene_number"): s for s in items if isinstance(s, dict) and s.get("scene_number")}
                for sc in needs_expansion:
                    sn = sc.get("scene_number")
                    if sn in expanded:
                        new_narr = expanded[sn].get("narration", "").strip()
                        if len(new_narr) > len(sc.get("narration", "")):
                            sc["narration"] = new_narr
                        new_dial = expanded[sn].get("dialogue")
                        if new_dial and isinstance(new_dial, list) and len(new_dial) > 0:
                            sc["dialogue"] = new_dial
                    else:
                        # Fallback enrichment if LLM missed this scene
                        narr = sc.get("narration", "").strip()
                        sc["narration"] = narr + " चारों तरफ गहरा सन्नाटा और बेचैनी छाई हुई थी। दिल की धड़कनें साफ़ सुनाई दे रही थीं और हर पल कोई अनहोनी होने का अंदेशा बढ़ रहा था।"
            except Exception as exc:
                logger.warning("Failed to expand batch %s-%s via LLM: %s — enriching locally", i, i + batch_size, exc)
                # Local fallback enrichment so scenes never stay as 1-sentence stubs
                for sc in needs_expansion:
                    narr = sc.get("narration", "").strip()
                    mood = (sc.get("mood") or "suspense").lower()
                    if "suspense" in mood or "horror" in mood:
                        sc["narration"] = narr + " चारों तरफ फैला गहरा अंधेरा और सन्नाटा रूह को कंपा रहा था। हर कदम पर ऐसा लग रहा था मानो कोई खौफ़नाक साया पीछे-पीछे चल रहा हो। दिल की धड़कनें इतनी तेज़ थीं कि गले तक आवाज़ आ रही थी।"
                    else:
                        sc["narration"] = narr + " आँखों के सामने तैरते सवालों का कोई जवाब नहीं मिल रहा था। मन में एक गहरा तूफ़ान उठ रहा था और दिल जानता था कि अब सच्चाई का सामना करने के सिवा कोई दूसरा रास्ता नहीं बचा है।"

        new_total = self._calculate_spoken_chars(story)
        logger.info("After expansion, story speech chars: %d (was %d)", new_total, current_chars)
        return story

    def _generate_fallback_story(self, req: StoryGenerationRequest, topic: dict[str, Any]) -> dict[str, Any]:
        """Procedural story generator used when external AI APIs are unavailable or rate-limited."""
        cat_id = req.category_id or "moral"
        topic_title = topic.get("main_topic") or "अनकहा रहस्य और कर्मों का सच"

        if "horror" in cat_id or "mystery" in cat_id:
            title = topic_title if "रहस्य" in topic_title else "पुरानी हवेली का खौफ़नाक रहस्य"
            characters = [
                {"name": "राघव", "gender": "male", "voice_tag": "male_1"},
                {"name": "माया", "gender": "female", "voice_tag": "female_1"},
            ]
            scenes = [
                {
                    "scene_number": 1,
                    "visual_description": "A dense foggy forest in front of an ancient abandoned Indian mansion at midnight, lightning in the sky.",
                    "image_prompt": "Cinematic photo of an ancient dark abandoned Indian haveli at stormy midnight, heavy rain, glowing lightning, ultra-detailed 8k",
                    "narration": "रात के बारह बज चुके थे और मूसलाधार बारिश में पुरानी हवेली के टूटे हुए दरवाज़े हवा के थपेड़ों से लगातार खड़खड़ा रहे थे। राघव और माया अपनी गाड़ी खराब होने के बाद इस सुनसान खंडहर में पनाह लेने पहुँचे थे। चारों तरफ फैली सीलन और धूल भरी खामोशी दिल में एक अजीब सी बेचैनी घोल रही थी।",
                    "dialogue": [
                        {"character": "राघव", "line": "यहाँ अंदर आ जाओ माया, बाहर तूफ़ान बहुत तेज़ है।", "gender": "male"},
                        {"character": "माया", "line": "राघव, इस जगह का माहौल कुछ ठीक नहीं लग रहा। क्या यहाँ कोई रहता है?", "gender": "female"},
                    ],
                },
                {
                    "scene_number": 2,
                    "visual_description": "A grand abandoned hall with spiderwebs, a massive grandfather clock ticking eerily.",
                    "image_prompt": "Ancient dusty hall inside an Indian palace, broken antique furniture, moonlight through broken windows, eerie suspenseful atmosphere",
                    "narration": "जैसे ही दोनों हवेली के बड़े दालान में दाखिल हुए, एक भारी लोहे की घंटी की गूंज दीवारों से टकराने लगी। सालों से बंद पड़े इस खंडहर में एक पुरानी घड़ी अचानक बिना चाबी के टिक-टिक करने लगी थी। हवा में अचानक जलते हुए दीए और चमेली के तेल की खुशबू फैलने लगी।",
                    "dialogue": [
                        {"character": "राघव", "line": "परेशान मत हो, शायद यह पुरानी घड़ी हवा के दबाव से चल पड़ी होगी।", "gender": "male"},
                        {"character": "माया", "line": "हवा से घड़ी चल सकती है राघव, लेकिन यह जलती हुई मोमबत्तियाँ किसने रखी हैं?", "gender": "female"},
                    ],
                },
                {
                    "scene_number": 3,
                    "visual_description": "A dark wooden staircase leading into shadows, strange muddy footprints on the stairs.",
                    "image_prompt": "Dramatic view of an ancient creaking wooden staircase in a dark palace, shadows stretching, cinematic moody lighting",
                    "narration": "सीढ़ियों के पास ताज़े गीले पैरों के निशान ऊपरी मंजिल की तरफ जा रहे थे। राघव ने अपनी टॉर्च की रोशनी सीढ़ियों के अंधेरे में डाली, लेकिन रोशनी कुछ ही दूरी पर जाकर जैसे काले कोहरे में समा जाती थी। ऊपर से किसी के भारी कदमों की धीमी आहट साफ़ सुनाई दे रही थी।",
                    "dialogue": [
                        {"character": "माया", "line": "राघव रुको! ऊपर मत जाओ, कोई हमारा पीछा कर रहा है।", "gender": "female"},
                        {"character": "राघव", "line": "अगर कोई है तो हमें सच जानना ही होगा, हम यहाँ छिपकर नहीं बैठ सकते।", "gender": "male"},
                    ],
                },
                {
                    "scene_number": 4,
                    "visual_description": "A locked room with an ancient iron lock covered in mysterious red symbols.",
                    "image_prompt": "Old wooden door with a heavy rusted padlock, mysterious red symbols, dark hallway, ominous glow",
                    "narration": "ऊपर की मंजिल पर एक पुराना बंद कमरा था जिसके दरवाज़े पर भारी लोहे का ताला लटक रहा था। दरवाज़े के नीचे से एक हल्की नीली रोशनी बाहर झांक रही थी। कमरे के अंदर से किसी के धीमे-धीमे रोने और फुसफुसाने की दर्दनाक आवाज़ें आ रही थीं।",
                    "dialogue": [
                        {"character": "माया", "line": "भगवान के लिए यहाँ से वापस चलो राघव, यह कोई इंसान नहीं है!", "gender": "female"},
                        {"character": "राघव", "line": "यह आवाज़ जानी-पहचानी लग रही है, जैसे कोई बरसों से मदद की गुहार लगा रहा हो।", "gender": "male"},
                    ],
                },
                {
                    "scene_number": 5,
                    "visual_description": "Inside the mysterious room, a large carved wooden chest emitting a soft golden glow.",
                    "image_prompt": "Mysterious antique wooden chest in the center of an empty room, intricate carvings, magical subtle glow, atmospheric dust motes",
                    "narration": "राघव ने भारी धक्का देकर दरवाज़ा खोला तो कमरा बिल्कुल खाली था, सिवाय बीच में रखे एक विशाल नक्काशीदार संदूक के। संदूक के ऊपर एक पुरानी डायरी और एक तस्वीर रखी हुई थी। तस्वीर में राघव के दादाजी का चेहरा साफ़ दिखाई दे रहा था।",
                    "dialogue": [
                        {"character": "राघव", "line": "यह... यह तो मेरे दादाजी की तस्वीर है! उनका इस हवेली से क्या रिश्ता था?", "gender": "male"},
                        {"character": "माया", "line": "डायरी देखो राघव, इस पर पचास साल पहले की तारीख लिखी है।", "gender": "female"},
                    ],
                },
                {
                    "scene_number": 6,
                    "visual_description": "Close up of an old yellowed diary page with faded Hindi writing and an antique key.",
                    "image_prompt": "Close-up of vintage yellowed journal pages with handwritten Hindi script, an ornate brass key beside it, dramatic candle lighting",
                    "narration": "डायरी के पन्नों में दफन सच्चाई पढ़कर दोनों के रोंगटे खड़े हो गए। पचास साल पहले इसी हवेली के मालिक ने गाँव के ग़रीब किसानों का खज़ाना छिपाया था, और राघव के दादाजी ने उस खज़ाने की रक्षा का वचन दिया था। लेकिन वो खज़ाना कभी बाहर नहीं आ सका क्योंकि हवेली में आग लग गई थी।",
                    "dialogue": [
                        {"character": "माया", "line": "तो यह हवेली भुतहा नहीं है, यहाँ तो उन किसानों की अमानत आज भी महफ़ूज़ है!", "gender": "female"},
                        {"character": "राघव", "line": "दादाजी का अधूरा वादा... आज मुझे हर हाल में पूरा करना होगा।", "gender": "male"},
                    ],
                },
                {
                    "scene_number": 7,
                    "visual_description": "The open chest revealing ancestral treasures and papers meant for village schools and welfare.",
                    "image_prompt": "Open antique chest with golden coins, deeds and ancient documents, warm lighting spreading in the room",
                    "narration": "जैसे ही राघव ने संदूक का ताला खोला, उसमें से सोने के सिक्कों के साथ गाँव के स्कूल और ज़मीनों के असली दस्तावेज़ निकले। उसी पल हवेली का भयानक अंधेरा और खौफ़नाक सन्नाटा एक सुकून भरी शांति में बदल गया, जैसे कोई बेचैन आत्मा हमेशा के लिए आज़ाद हो गई हो।",
                    "dialogue": [
                        {"character": "राघव", "line": "माया, कल सुबह यह सारा खज़ाना और ज़मीनें गाँव वालों को सौंप दी जाएँगी।", "gender": "male"},
                        {"character": "माया", "line": "तुम्हारे दादाजी की आत्मा को आज सच में शांति मिल गई राघव।", "gender": "female"},
                    ],
                },
                {
                    "scene_number": 8,
                    "visual_description": "Early sunrise over the peaceful mansion and nearby village, warm morning rays cutting through mist.",
                    "image_prompt": "Beautiful golden sunrise over an ancient Indian village and mansion, mist dissolving, rays of hope, cinematic wide angle",
                    "narration": "सुबह की पहली सुनहरी किरण हवेली की खिड़कियों से अंदर आई तो सारा डर काफूर हो चुका था। जिस हवेली को लोग सालों से खौफ़ का साया समझते थे, वो दरअसल एक निष्ठावान वादे और सच्चाई की अमानत थी। राघव और माया ने मुस्कुराते हुए नई सुबह का स्वागत किया।",
                    "dialogue": [
                        {"character": "राघव", "line": "डर सिर्फ सच से अनजान होने का नाम है, सच सामने आते ही सब रोशन हो जाता है।", "gender": "male"},
                        {"character": "माया", "line": "चलो, गाँव के लोगों को उनकी खुशियाँ लौटाने का समय हो गया है।", "gender": "female"},
                    ],
                },
            ]
            synopsis = "पुरानी हवेली में रात बिताने पहुँचे दो मुसाफ़िरों को खौफ़नाक सायों के पीछे एक 50 साल पुराने वादे और खज़ाने का चौंकाने वाला सच मिलता है।"
            moral = "डर तभी तक डराता है जब तक सच सामने नहीं आता। ईमानदारी और वचन की शक्ति हर अंधेरे को मिटा देती है।"

        else:
            # Moral / Village / General
            title = topic_title if len(topic_title) > 6 else "कर्मों का सच्चा हिसाब और अनमोल सीख"
            characters = [
                {"name": "माधव", "gender": "male", "voice_tag": "male_1"},
                {"name": "सुमित्रा", "gender": "female", "voice_tag": "female_1"},
            ]
            scenes = [
                {
                    "scene_number": 1,
                    "visual_description": "An honest potter working on clay wheel outside a humble mud house in an Indian village during golden dusk.",
                    "image_prompt": "Humble Indian potter shaping clay pot on wooden wheel outside village hut, golden sunset light, cinematic realism, 8k",
                    "narration": "गाँव के एक छोटे से कोने में माधव अपनी पत्नी सुमित्रा के साथ मिट्टी के बर्तन बनाकर ईमानदारी से ज़िंदगी बसर कर रहा था। माधव की बनाई मटकियों में एक खास मिठास थी, लेकिन गरीबी उसका पीछा नहीं छोड़ रही थी। फिर भी माधव कभी बेईमानी के रास्ते पर नहीं चला।",
                    "dialogue": [
                        {"character": "सुमित्रा", "line": "माधव, आज बाज़ार में सब बर्तन बिक गए क्या? घर में राशन खत्म होने वाला है।", "gender": "female"},
                        {"character": "माधव", "line": "चिंता मत करो सुमित्रा, ईश्वर पर भरोसा रखो। मेहनत की कमाई में हमेशा बरकत होती है।", "gender": "male"},
                    ],
                },
                {
                    "scene_number": 2,
                    "visual_description": "A wealthy arrogant merchant riding through the dusty village path looking down upon villagers.",
                    "image_prompt": "Wealthy arrogant Indian landlord on decorated cart in dusty village street, villagers looking with concern, rich textures",
                    "narration": "उसी गाँव का सबसे अमीर साहूकार धनपत राय हर किसी की मजबूरी का फायदा उठाकर उनकी ज़मीनें हड़प लेता था। धनपत का मानना था कि दुनिया में सिर्फ दौलत की कीमत होती है, इंसानियत और ईमानदारी की कोई औकात नहीं।",
                    "dialogue": [
                        {"character": "माधव", "line": "साहूकार जी, गाँव के गरीब किसानों का कर्ज़ थोड़ा कम कर दीजिए, सब परेशान हैं।", "gender": "male"},
                        {"character": "सुमित्रा", "line": "इन्हें समझाने का कोई फायदा नहीं माधव, पत्थर पर पानी डालने से फूल नहीं खिलते।", "gender": "female"},
                    ],
                },
                {
                    "scene_number": 3,
                    "visual_description": "A dusty road near the river where a leather pouch full of gold coins lies forgotten in the grass.",
                    "image_prompt": "Old leather pouch bursting with gold coins lying on dirt pathway near riverbank, tall grass, dramatic lighting",
                    "narration": "एक शाम जब माधव नदी किनारे चिकनी मिट्टी लेने गया, तो पगडंडी की झाड़ियों में उसे एक भारी चमड़े की थैली दिखाई दी। जब उसने थैली खोली, तो उसमें चमकती हुई सोने की अशर्फियां और साहूकार के बहीखाते के ज़रूरी कागज़ात थे।",
                    "dialogue": [
                        {"character": "माधव", "line": "हे भगवान! यह तो साहूकार धनपत का खोया हुआ बटुआ है, जिसमें उनकी सारी दौलत है।", "gender": "male"},
                        {"character": "सुमित्रा", "line": "यह किसी की मेहनत की या खोई हुई चीज़ है माधव, इसे तुरंत लौटाना हमारा फ़र्ज़ है।", "gender": "female"},
                    ],
                },
                {
                    "scene_number": 4,
                    "visual_description": "Madhav standing at the grand mansion gate of the wealthy merchant holding the leather bag.",
                    "image_prompt": "Humble villager standing in front of grand carved wooden doors of an Indian mansion, holding leather bag, evening glow",
                    "narration": "माधव बिना एक पल गंवाए सीधे साहूकार की हवेली पहुँचा। हवेली में मातम का माहौल था क्योंकि साहूकार का सारा खज़ाना उसी थैली में था और वह सदमे से बीमार पड़ चुका था। माधव ने आगे बढ़कर पूरी थैली साहूकार के पैरों में रख दी।",
                    "dialogue": [
                        {"character": "माधव", "line": "साहूकार जी, आपकी यह अमानत मुझे नदी किनारे मिली थी। संभालिए, एक भी सिक्का कम नहीं है।", "gender": "male"},
                        {"character": "सुमित्रा", "line": "हमें आपके पैसे नहीं चाहिए, बस आप ठीक हो जाइए यही प्रार्थना है।", "gender": "female"},
                    ],
                },
                {
                    "scene_number": 5,
                    "visual_description": "The wealthy merchant looking with wide eyes of shock and shame at the honest poor couple.",
                    "image_prompt": "Elderly wealthy Indian merchant with tears of remorse looking at poor honest man, rich hall background, emotional depth",
                    "narration": "साहूकार की आँखें फटी की फटी रह गईं। जिस गरीब कुम्हार को वह तुच्छ समझता था, उसी ने बिना किसी लालच के उसकी ज़िंदगी भर की कमाई बिना छुए लौटा दी थी। साहूकार के अंदर का अहंकार एक ही पल में चकनाचूर हो गया।",
                    "dialogue": [
                        {"character": "माधव", "line": "ईमानदारी की रोटी सूखी भले हो, लेकिन रात को चैन की नींद उसी से आती है।", "gender": "male"},
                        {"character": "सुमित्रा", "line": "दौलत तो हाथ का मैल है, इंसान के साथ केवल उसके नेक कर्म ही जाते हैं।", "gender": "female"},
                    ],
                },
                {
                    "scene_number": 6,
                    "visual_description": "The merchant tearing up the debt papers of all poor villagers in front of the village panchayat.",
                    "image_prompt": "Indian village panchayat meeting under banyan tree, merchant burning debt contracts, emotional villagers clapping",
                    "narration": "अगली सुबह साहूकार ने पूरे गाँव को बरगद के पेड़ के नीचे बुलाया। माधव की ईमानदारी ने साहूकार का दिल हमेशा के लिए बदल दिया था। उसने भरे समाज में सभी गरीब किसानों के कर्ज़ के कागज़ात फाड़ दिए और गाँव वालों की ज़मीनें वापस लौटा दीं।",
                    "dialogue": [
                        {"character": "माधव", "line": "साहूकार जी, आज आपने सच में असली अमीरी का मतलब समझ लिया है।", "gender": "male"},
                        {"character": "सुमित्रा", "line": "जब दिल बड़ा हो जाए, तो पूरी दुनिया अपनी लगने लगती है।", "gender": "female"},
                    ],
                },
                {
                    "scene_number": 7,
                    "visual_description": "Villagers celebrating together, Madhav and Sumitra honored with flower garlands.",
                    "image_prompt": "Joyous celebration in Indian village, colorful marigold garlands, smiling villagers, festive atmosphere",
                    "narration": "गाँव भर में खुशियों की लहर दौड़ गई। साहूकार ने माधव को गाँव के कुटीर उद्योग का मुख्य प्रबंधक बनाया और उसे गाँव के बच्चों के स्कूल की ज़िम्मेदारी सौंपी। ईमानदारी की खुशबू पूरे देहात में महक उठी थी।",
                    "dialogue": [
                        {"character": "माधव", "line": "देखा सुमित्रा, सच्चाई का रास्ता कठिन ज़रूर होता है, लेकिन मंज़िल बहुत खूबसूरत होती है।", "gender": "male"},
                        {"character": "सुमित्रा", "line": "सच है माधव, अच्छे कर्मों का फल देर से सही, लेकिन मिलता ज़रूर है।", "gender": "female"},
                    ],
                },
                {
                    "scene_number": 8,
                    "visual_description": "Madhav teaching young village children to shape clay under the golden afternoon sun, peaceful community.",
                    "image_prompt": "Warm golden scene of potter teaching village children to make earthen lamps, smiling faces, peaceful village backdrop",
                    "narration": "माधव के जीवन ने यह साबित कर दिया कि दौलत से इंसान बड़ा नहीं बनता, बल्कि उसकी नीयत और कर्म ही उसका असली परिचय होते हैं। जो दूसरों के लिए भलाई बोता है, उसकी ज़िंदगी में हमेशा खुशियों की फसल लहलहाती है।",
                    "dialogue": [
                        {"character": "माधव", "line": "हमेशा याद रखना बच्चों, सच्चाई की राह पर कभी कदम मत डगमगाना।", "gender": "male"},
                        {"character": "सुमित्रा", "line": "नेक नीयत ही इंसान की सबसे बड़ी पूँजी है।", "gender": "female"},
                    ],
                },
            ]
            synopsis = "गरीब कुम्हार माधव को साहूकार का सोने से भरा बटुआ मिलता है। उसकी ईमानदारी साहूकार का कठोर दिल बदल देती है और पूरे गाँव की किस्मत संवर जाती है।"
            moral = "ईमानदारी और नेक नीयत सबसे बड़ी दौलत है। अच्छे कर्म कभी व्यर्थ नहीं जाते और एक दिन दुनिया को बदलकर रख देते हैं।"

        return {
            "title": title,
            "synopsis": synopsis,
            "scenes": scenes,
            "characters": characters,
            "moral": moral,
            "ending": "सच्चाई और अच्छाई की हमेशा जीत होती है।",
            "call_to_action": "अगर आपको यह कहानी पसंद आई, तो वीडियो को लाइक करें और ऐसी ही प्रेरणादायक कहानियों के लिए चैनल को सब्सक्राइब करें।",
            "story_project_id": 1,
        }
