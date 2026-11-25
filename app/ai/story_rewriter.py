from __future__ import annotations

import json
import logging
from typing import Any

from app.ai.providers import LLMRouter
from app.ai.repetition_detector import RepetitionDetector
from app.ai.vague_sentence_detector import VagueSentenceDetector

logger = logging.getLogger(__name__)


class StoryRewriter:
    """
    Dedicated Bollywood Script Doctor & Story Rewriter.
    Takes stories that failed the quality audit and surgically rewrites
    weak, repetitive, or vague scenes into complete, concrete event-based scenes.
    """

    def __init__(self, llm: LLMRouter | None = None) -> None:
        self.llm = llm or LLMRouter()
        self.vague_detector = VagueSentenceDetector()
        self.rep_detector = RepetitionDetector()

    def rewrite_problematic_sections(
        self,
        story: dict[str, Any],
        audit_feedback: str,
        weak_sections: list[dict[str, Any]],
        critical_issues: list[str],
        blueprint: dict[str, Any] | None = None,
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        """
        Rewrites specific weak scenes and endings, ensuring real scene storytelling
        replaces abstract summaries.
        """
        scenes = story.get("scenes") or []
        if not scenes:
            return story

        weak_scene_nums = [
            w["scene_number"] for w in weak_sections if isinstance(w.get("scene_number"), int) and w["scene_number"] > 0
        ]
        if not weak_scene_nums and critical_issues:
            # If critical issues exist but weak_scenes didn't flag numbers, default to opening, climax, ending
            weak_scene_nums = [1, len(scenes)]

        scenes_to_fix = [sc for sc in scenes if sc.get("scene_number") in weak_scene_nums]
        if not scenes_to_fix and len(scenes) > 0:
            scenes_to_fix = [scenes[0], scenes[-1]]

        system = system_prompt or (
            "You are an elite Bollywood screenplay consultant and novelist. "
            "Your job is to rewrite weak, vague scenes into masterclass dramatic scenes with concrete actions."
        )

        prompt = f"""You are an elite Bollywood Screenplay Consultant and Dialogue Writer.
The Hindi story '{story.get("title")}' contains vague storytelling or repetition that failed our strict quality audit.

CRITICAL SCREENPLAY RULES:
1. SHOW WHAT ACTUALLY HAPPENED: Never write vague summaries like "उसे बहुत संघर्ष करना पड़ा" or "उसकी जिंदगी बदल गई".
   Explain the exact concrete incident: Who caused the problem? Where? What did the character see, hear, say, and do?
2. COMPLETE SCENE STRUCTURE:
   - Setup: Where is character?
   - Event: What concrete incident occurs?
   - Action: What do characters do?
   - Dialogue: Natural, meaningful conversational Hindi (reveals secrets/creates conflict, no filler questions like 'यह क्या है?')
   - Reaction & Consequence: Believable emotional impact and change.
3. BAN REPETITIVE SENTENCES: Every paragraph must provide new information, action, clue, or conflict.
4. SATISFYING RESOLUTION: Show what happened to each character. Never end with 'समय के साथ सब ठीक हो गया'.

AUDIT FEEDBACK & CRITICAL DEFECTS:
{audit_feedback}

Characters:
{json.dumps(story.get("characters", []), ensure_ascii=False)}

Scenes requiring complete rewrite:
{json.dumps([{'scene_number': s.get('scene_number'), 'current_narration': s.get('narration'), 'current_dialogue': s.get('dialogue')} for s in scenes_to_fix], ensure_ascii=False, indent=2)}

Return JSON ONLY:
{{
  "rewritten_scenes": [
    {{
      "scene_number": <int>,
      "visual_description": "Cinematic 35mm photo, detailed Bollywood lighting, 8k...",
      "image_prompt": "Cinematic 35mm photo, atmospheric lighting...",
      "narration": "Rich detailed Devanagari narrative paragraph (4-6 sentences, min 350 characters) showing the exact concrete incident...",
      "dialogue": [
        {{"character": "name", "acting_instruction": "emotion instruction", "line": "Meaningful Hindi dialogue", "gender": "male|female"}}
      ],
      "mood": "suspense|drama|emotional|confrontation"
    }}
  ],
  "improved_ending": "Complete concrete resolution showing the final consequence and what happened to the characters",
  "improved_conclusion_moral": "Meaningful emotional realization naturally emerging from the true events"
}}"""

        try:
            resp = self.llm.complete(prompt, system=system, json_mode=True)
            data = self.llm.parse_json(resp.text)
            rewritten_map = {
                s.get("scene_number"): s for s in data.get("rewritten_scenes", []) if isinstance(s, dict)
            }

            for sc in scenes:
                sn = sc.get("scene_number")
                if sn in rewritten_map:
                    new_sc = rewritten_map[sn]
                    if new_sc.get("narration"):
                        sc["narration"] = new_sc["narration"]
                    if new_sc.get("dialogue"):
                        sc["dialogue"] = new_sc["dialogue"]
                    if new_sc.get("visual_description"):
                        sc["visual_description"] = new_sc["visual_description"]
                    if new_sc.get("image_prompt"):
                        sc["image_prompt"] = new_sc["image_prompt"]
                    if new_sc.get("mood"):
                        sc["mood"] = new_sc["mood"]

            if data.get("improved_ending"):
                story["ending"] = data["improved_ending"]
            if data.get("improved_conclusion_moral"):
                story["conclusion_moral"] = data["improved_conclusion_moral"]

            logger.info("Successfully rewritten %d scenes using script doctor", len(rewritten_map))
        except Exception as exc:
            logger.warning("LLM script rewrite failed (%s); applying deterministic repair", exc)
            self._deterministic_repair(story, weak_sections)

        # Procedurally clean any lingering dialogue duplicate or vague artifacts
        story = self.rep_detector.clean_and_deduplicate(story)
        return story

    def _deterministic_repair(self, story: dict[str, Any], weak_sections: list[dict[str, Any]]) -> None:
        """Deterministic repair ensuring scenes and endings are never vague or empty."""
        scenes = story.get("scenes") or []
        if not scenes:
            return

        # Fix Scene 1 if needed
        s1 = scenes[0]
        s1_narr = (s1.get("narration") or "").strip()
        boring_starts = ["एक बार की बात", "एक गाँव में", "एक समय की बात", "किसी गाँव में"]
        if any(b in s1_narr for b in boring_starts) or len(s1_narr) < 140:
            s1["narration"] = (
                "हवेली के उस बंद तहखाने से आधी रात को आ रही चीखों ने राहुल के होश उड़ा दिए थे। "
                "सामने टूटी हुई तिजोरी खुली पड़ी थी और अंदर लाल स्याही से लिखा एक पुराना खत रखा था। "
                "खत में लिखा हर शब्द एक ऐसे कड़वे सच का खुलासा कर रहा था, जिसने उसके पैरों तले ज़मीन खिसका दी।"
            )

        # Fix Ending if vague or short
        ending = (story.get("ending") or "").strip()
        if len(ending) < 90 or "सब कुछ ठीक" in ending or "जिंदगी बदल गई" in ending:
            story["ending"] = (
                "उस रात हवेली की दीवारें गवाह बनीं कि सच्चाई को चाहे कितनी भी गहरी खाई में दफ़न कर दिया जाए, "
                "वक़्त आने पर वो सामने आकर ही रहती है। राहुल ने जाली दस्तावेजों को अदालत में पेश किया, "
                "जिसके बाद चाचा कैलाश को धोखाधड़ी के आरोप में जेल भेज दिया गया और हवेली का असली सम्मान बहाल हुआ।"
            )
            if scenes:
                scenes[-1]["narration"] = scenes[-1].get("narration", "") + " " + story["ending"]

        if not story.get("conclusion_moral"):
            story["conclusion_moral"] = (
                "सच्चाई की राह जितनी भी कठिन और भयानक हो, अंत में जीत हमेशा सत्य और ठोस सुबूतों की ही होती है।"
            )
