from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from app.ai.providers import LLMRouter

logger = logging.getLogger(__name__)


@dataclass
class StoryBlueprint:
    central_concept: str
    main_character: dict[str, Any]
    supporting_characters: list[dict[str, Any]]
    character_relationships: dict[str, str]
    character_motivations: dict[str, str]
    main_conflict: dict[str, Any]
    antagonist_or_opposing_force: dict[str, Any]
    important_events: list[dict[str, Any]]
    hidden_clues: list[dict[str, Any]]
    cause_and_effect_timeline: list[str]
    major_twist: dict[str, Any]
    climax: dict[str, Any]
    final_resolution: dict[str, Any]
    conclusion_moral: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "central_concept": self.central_concept,
            "main_character": self.main_character,
            "supporting_characters": self.supporting_characters,
            "character_relationships": self.character_relationships,
            "character_motivations": self.character_motivations,
            "main_conflict": self.main_conflict,
            "antagonist_or_opposing_force": self.antagonist_or_opposing_force,
            "important_events": self.important_events,
            "hidden_clues": self.hidden_clues,
            "cause_and_effect_timeline": self.cause_and_effect_timeline,
            "major_twist": self.major_twist,
            "climax": self.climax,
            "final_resolution": self.final_resolution,
            "conclusion_moral": self.conclusion_moral,
        }


class StoryBlueprintGenerator:
    """
    Generates a rigorous Bollywood screenplay blueprint prior to scene-by-scene drafting.
    Ensures that every twist has planted clues, every action has motivation,
    and no story relies on vague or random incidents.
    """

    def __init__(self, llm: LLMRouter | None = None) -> None:
        self.llm = llm or LLMRouter()

    def generate_blueprint(
        self,
        genre: str,
        category_name: str,
        topic: dict[str, Any],
        target_scene_count: int,
        is_short: bool,
    ) -> dict[str, Any]:
        """
        Creates a structured screenplay blueprint via LLM with strict Bollywood storytelling rules.
        Falls back to procedural blueprint if LLM is unavailable.
        """
        topic_title = topic.get("main_topic") or f"{category_name} - रोमांचक कथा"
        hook_angle = topic.get("angle") or topic.get("hook") or "अचानक हुआ रहस्यमयी खुलासा"

        prompt = f"""You are a master Bollywood Screenwriter and Story Architect.
Create a complete, detailed Plot Blueprint for a high-retention Hindi YouTube story.

Theme/Topic: {topic_title}
Genre: {genre}
Category: {category_name}
Angle/Hook: {hook_angle}
Target Scene Count: {target_scene_count} scenes ({'Short 60s' if is_short else 'Long-form 10-15 min'})

CRITICAL RULES:
1. SHOW, DON'T TELL: No vague summaries like "उसे बहुत संघर्ष करना पड़ा". Every conflict must be an exact event (who did what, where, when, what was said).
2. LOGICAL CAUSE-AND-EFFECT: Event A directly triggers Event B. No disconnected random accidents.
3. FORESHADOWED TWIST: The major twist must rely on hidden clues planted in early scenes, not an arbitrary sudden stranger.
4. SATISFYING RESOLUTION: Completely resolve the central mystery and conflict. Never end with "समय बीतता गया सब ठीक हो गया".

Return JSON ONLY in this schema:
{{
  "central_concept": "Core premise and high stakes in 1-2 sharp sentences",
  "main_character": {{
    "name": "Devanagari name (e.g. राघव)",
    "gender": "male|female",
    "age_group": "e.g. 28 years old",
    "occupation": "Specific job/role",
    "personality": "Core traits and inner flaw",
    "signature_attire": "Detailed appearance for consistent AI visual generation"
  }},
  "supporting_characters": [
    {{
      "name": "Name",
      "gender": "male|female",
      "role": "Role in story",
      "relationship_to_protagonist": "Exact relation",
      "signature_attire": "Visual description"
    }}
  ],
  "character_relationships": {{
    "CharacterA and CharacterB": "Underlying tension, secret, or bond"
  }},
  "character_motivations": {{
    "MainCharacter": "Concrete urgent objective (e.g. prove father innocent before eviction in 48 hours)"
  }},
  "main_conflict": {{
    "what_happened": "Exact incident that disrupted normal life",
    "who_caused_it": "Person or force responsible",
    "where_and_when": "Exact physical location and time",
    "stakes": "What is lost if protagonist fails"
  }},
  "antagonist_or_opposing_force": {{
    "name": "Name of opposing character or authority",
    "hidden_motive": "Why they are doing this (greed, revenge, fear)",
    "leverage": "What power they hold over protagonist"
  }},
  "important_events": [
    {{
      "event_number": 1,
      "location": "Physical setting",
      "what_happens": "Concrete action/incident",
      "conflict_or_obstacle": "Obstacle faced",
      "consequence": "Direct consequence driving next event"
    }}
  ],
  "hidden_clues": [
    {{
      "clue": "Physical object, misplaced letter, timestamp, torn fabric, signature discrepancy",
      "planted_in_scene": 1,
      "revealed_in_scene": {target_scene_count - 2},
      "significance": "How it dismantles the lie"
    }}
  ],
  "cause_and_effect_timeline": [
    "Step 1 causes Step 2",
    "Step 2 forces Step 3"
  ],
  "major_twist": {{
    "false_belief": "What characters and audience believed till now",
    "shocking_truth": "The actual truth revealed",
    "logical_setup": "Which earlier clues proved this"
  }},
  "climax": {{
    "location": "High stakes confrontation setting",
    "confrontation": "How protagonist confronts antagonist with concrete evidence",
    "turning_point": "Critical action or confession"
  }},
  "final_resolution": {{
    "what_happened_to_main_character": "Clear tangible outcome",
    "what_happened_to_antagonist": "Clear legal, emotional, or karmic consequence",
    "mystery_status": "Completely solved",
    "final_emotional_scene": "Concrete final visual moment"
  }},
  "conclusion_moral": "Deep philosophical or emotional realization emerging naturally from events"
}}"""

        try:
            resp = self.llm.complete(
                prompt,
                system="You are an elite Bollywood screenplay consultant. Output valid JSON only.",
                json_mode=True,
            )
            blueprint_dict = self.llm.parse_json(resp.text)
            logger.info("Successfully generated screenplay blueprint for: %s", topic_title)
            return blueprint_dict
        except Exception as exc:
            logger.warning("LLM blueprint generation failed (%s); generating procedural blueprint.", exc)
            return self._procedural_fallback_blueprint(genre, category_name, topic, target_scene_count)

    def _procedural_fallback_blueprint(
        self, genre: str, category_name: str, topic: dict[str, Any], target_scene_count: int
    ) -> dict[str, Any]:
        """Provides a richly textured fallback blueprint with zero vague elements."""
        topic_title = topic.get("main_topic") or "हवेली का वसीयतनामा और आधी रात का सच"
        return {
            "central_concept": "पिता की आकस्मिक मृत्यु के बाद पैतृक मकान खाली करने का नोटिस मिलता है, जिसके पीछे चाचा की जाली वसीयत और 20 साल पुराना छिपा हुआ सच है।",
            "main_character": {
                "name": "राहुल",
                "gender": "male",
                "age_group": "27 years old",
                "occupation": "सॉफ्टवेयर इंजीनियर",
                "personality": "शांत, तार्किक, लेकिन परिवार के सम्मान के लिए किसी भी हद तक जाने वाला",
                "signature_attire": "गहरे नीले रंग की जैकेट, सफेद कॉटन शर्ट, हाथ में पुरानी टाइटन घड़ी",
            },
            "supporting_characters": [
                {
                    "name": "चाचा कैलाश",
                    "gender": "male",
                    "role": "विरोधी (Antagonist)",
                    "relationship_to_protagonist": "सगे चाचा",
                    "signature_attire": "सफेद कुर्ता-पायजामा, गले में सोने की मोटी चेन, तीखी मूंछें",
                },
                {
                    "name": "शालिनी",
                    "gender": "female",
                    "role": "सहयोगी और वकील",
                    "relationship_to_protagonist": "बचपन की दोस्त",
                    "signature_attire": "काले कोट में फॉर्मल वकील की पोशाक, चश्मा",
                },
            ],
            "character_relationships": {
                "राहुल और चाचा कैलाश": "दिखावे का अपनापन लेकिन संपत्ति को लेकर 15 साल पुरानी रंजिश",
                "राहुल और शालिनी": "गहरा भरोसा और कानूनी समर्थन",
            },
            "character_motivations": {
                "राहुल": "72 घंटे के अंदर पिता के असली दस्तखत और बैंक के दस्तावेज ढूंढकर घर को नीलाम होने से बचाना",
                "चाचा कैलाश": "जाली वसीयत के सहारे प्राइम लोकेशन की 5 करोड़ की पुश्तैनी हवेली हड़पना",
            },
            "main_conflict": {
                "what_happened": "चाचा ने पिता के अंतिम संस्कार के ठीक तीसरे दिन एक गिरवीनामा दिखाया जिसमें दावा किया गया कि पिता ने 40 लाख का कर्ज़ लिया था",
                "who_caused_it": "चाचा कैलाश और उसका बैंक मैनेजर साथी",
                "where_and_when": "हवेली के मुख्य बरामदे में शाम 6 बजे",
                "stakes": "राहुल और उसकी बीमार माँ बेघर हो जाएंगे और पिता पर धोखेबाज़ का कलंक लगेगा",
            },
            "antagonist_or_opposing_force": {
                "name": "चाचा कैलाश",
                "hidden_motive": "सट्टे में डूबे 1 करोड़ रुपये चुकाने के लिए हवेली बेचकर भागना",
                "leverage": "कोर्ट का स्टे ऑर्डर और पिता के फर्जी हस्ताक्षर वाले स्टैम्प पेपर",
            },
            "important_events": [
                {
                    "event_number": 1,
                    "location": "हवेली का मुख्य गेट",
                    "what_happens": "चाचा कोर्ट का नोटिस लेकर बुलडोज़र के साथ पहुँचता है",
                    "conflict_or_obstacle": "राहुल के पास तत्काल कोई सबूत नहीं है",
                    "consequence": "राहुल 48 घंटे की मोहलत मांगता है और पिता के पुराने कमरे की तलाशी शुरू करता है",
                },
                {
                    "event_number": 2,
                    "location": "पिता की पुरानी लाइब्रेरी",
                    "what_happens": "पुरानी अलमारी के पीछे एक लोहे की तिजोरी और पिता की लाल डायरी मिलती है",
                    "conflict_or_obstacle": "तिजोरी का कोड पिता की जन्मतिथि नहीं है",
                    "consequence": "डायरी के पन्नों में चाचा द्वारा ब्लैकमेल किए जाने की तारीखें दर्ज मिलती हैं",
                },
            ],
            "hidden_clues": [
                {
                    "clue": "स्टैम्प पेपर की खरीद तारीख 2018 की है, लेकिन स्टैम्प वेंडर का लाइसेंस 2021 में जारी हुआ था",
                    "planted_in_scene": 1,
                    "revealed_in_scene": target_scene_count - 2,
                    "significance": "यह साबित करता है कि स्टैम्प पेपर बैक-डेट में खरीदा गया फर्जी दस्तावेज़ है",
                },
                {
                    "clue": "पिता के चश्मे के कवर में छिपा बैंक का ओरिजिनल नो-ड्यूज सर्टिफिकेट",
                    "planted_in_scene": 2,
                    "revealed_in_scene": target_scene_count - 1,
                    "significance": "प्रमाणित करता है कि कर्ज़ 5 साल पहले ही पूरी तरह चुकता हो चुका था",
                },
            ],
            "cause_and_effect_timeline": [
                "चाचा के फर्जी नोटिस की वजह से राहुल पिता के पुराने कागज़ात खंगालता है",
                "कागज़ात से पता चलता है कि स्टैम्प पेपर फर्जी है, जिससे राहुल सीधे वेंडर तक पहुँचता है",
                "वेंडर से चाचा के खिलाफ लिखित गवाही मिलती है, जिससे क्लाइमेक्स में पुलिस के सामने पोल खुलती है",
            ],
            "major_twist": {
                "false_belief": "पिता कर्ज़ में डूबे थे और उन्होंने आत्महत्या जैसी स्थिति में जान गंवाई थी",
                "shocking_truth": "पिता ने सारा कर्ज़ चुका दिया था और चाचा की सट्टेबाज़ी की शिकायत पुलिस में दर्ज कराने वाले थे",
                "logical_setup": "पिता की डायरी में लिखी तारीख और बैंक मैनेजर का गुप्त तबादला",
            },
            "climax": {
                "location": "हवेली का आंगन जहाँ चाचा रजिस्ट्री के कागजात पर ज़बरन हस्ताक्षर कराने आता है",
                "confrontation": "राहुल पुलिस और फॉरेंसिक रिपोर्ट के साथ चाचा और फर्जी मैनेजर को रंगे हाथों पकड़वाता है",
                "turning_point": "फॉरेंसिक एक्सपर्ट स्टैम्प पेपर की स्याही और फर्जी दस्तखत को ऑन-द-स्पॉट खारिज करता है",
            },
            "final_resolution": {
                "what_happened_to_main_character": "राहुल के नाम हवेली का कानूनी मालिकाना हक बहाल होता है, पिता की प्रतिष्ठा वापस मिलती है",
                "what_happened_to_antagonist": "चाचा कैलाश और उसका साथी धोखाधड़ी और जालसाज़ी के आरोप में जेल भेजे जाते हैं",
                "mystery_status": "वसीयत और कर्ज़ का रहस्य 100% सुलझ चुका है",
                "final_emotional_scene": "राहुल पिता की तस्वीर पर माला चढ़ाकर खिड़की खोलता है, जहाँ सुबह की ताज़ी धूप पूरे घर को रोशन कर देती है",
            },
            "conclusion_moral": "सच्चाई के दस्तावेज भले ही धूल में दब जाएं, लेकिन जब साहस और तर्क के साथ उन्हें तलाशा जाता है, तो झूठ की बड़ी से बड़ी दीवार ढह जाती है।",
        }
