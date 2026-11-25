from __future__ import annotations

import json
import logging
from typing import Any

from app.ai.providers import LLMRouter

logger = logging.getLogger(__name__)


class SceneBasedStoryWriter:
    """
    Writes complete, cinematic, scene-based Hindi stories from a plot blueprint.
    Enforces Bollywood screenplay structure:
    A. SETUP
    B. EVENT
    C. ACTION
    D. DIALOGUE
    E. REACTION
    F. CONSEQUENCE
    G. NEXT DEVELOPMENT
    Zero vague summaries. Zero empty repetitive sentences.
    """

    def __init__(self, llm: LLMRouter | None = None) -> None:
        self.llm = llm or LLMRouter()

    def write_story(
        self,
        blueprint: dict[str, Any],
        genre: str,
        category_name: str,
        language: str,
        target_duration_sec: int,
        target_scene_count: int,
        is_short: bool,
        system_prompt: str,
        visual_style: str | None = None,
    ) -> dict[str, Any]:
        """Drafts the story from the blueprint using LLM, with fallback to procedural storytelling."""
        prompt = f"""You are an elite Bollywood Screenplay Writer, Hindi Novelist, and Dialogue Writer.
Write a full cinematic story script in Hindi based on the provided Plot Blueprint.

GENRE: {genre}
CATEGORY: {category_name}
TARGET DURATION: {target_duration_sec} seconds
FORMAT: {"Vertical Short (9:16)" if is_short else "Cinematic Long-form (16:9)"}
EXACT SCENE COUNT: {target_scene_count} scenes

PLOT BLUEPRINT:
{json.dumps(blueprint, ensure_ascii=False, indent=2)}

STRICT WRITING RULES:
1. SHOW WHAT ACTUALLY HAPPENED (SHOW, DON'T TELL):
   - Whenever mentioning a problem, struggle, betrayal, argument, crime, or secret:
     NEVER write vague summaries like "उसे बहुत परेशानियों का सामना करना पड़ा" or "उसकी जिंदगी बदल गई".
   - You MUST describe the actual incident: What happened? Who caused it? Where? What did the character see, hear, say, do?
2. COMPLETE SCENE STRUCTURE FOR EVERY IMPORTANT EVENT:
   - Setup: Where is the character? What is happening?
   - Event: What exact concrete incident occurs?
   - Action: What physical actions do the characters take?
   - Dialogue: Substantive spoken Hindi that reveals information, creates conflict, or changes situation.
   - Reaction & Consequence: Tangible physical and emotional reaction and what changes.
3. BAN REPETITIVE SENTENCES:
   - NEVER repeat the same information using different words just to fill duration.
   - Every paragraph must contribute new information, new action, new clue, or new consequence.
4. MEANINGFUL DIALOGUE ONLY:
   - NO filler question loops like 'यह क्या है?', 'तुम कौन हो?', 'क्या हुआ?'.
   - Characters speak in natural conversational Hindi with distinct voices and realistic emotion.
5. NO DOUBLE AUDIO:
   - Narration sets the scene context; dialogue speaks the character's exact words.
   - Never quote character dialogue inside the narration field!
6. AI VISUALS:
   - visual_description and image_prompt MUST be in English for AI image generator.

Return JSON ONLY in this schema:
{{
  "title": "Compelling Devanagari Hindi Title",
  "synopsis": "Engaging 1-2 sentence Devanagari synopsis",
  "characters": [
    {{
      "name": "Devanagari name",
      "gender": "male|female",
      "age_group": "e.g. 27 years old",
      "description": "English visual description for character consistency",
      "voice_id_hint": "hi_IN-pratham-medium"
    }}
  ],
  "character_references": [
    {{
      "name": "Devanagari name",
      "gender": "male|female",
      "age_group": "27 years old",
      "physical_appearance": "Detailed physical features, height, hair, face in English",
      "signature_attire": "Exact clothes, colors, and accessories in English",
      "personality": "Observant, emotionally grounded, fearless"
    }}
  ],
  "hook_opening": "First 1-2 gripping sentences of Scene 1",
  "scenes": [
    {{
      "scene_number": 1,
      "story_beat": "opening_hook|setup|investigation|clue_discovery|conflict|twist|climax|resolution",
      "duration_estimate_sec": 45,
      "visual_description": "Cinematic 35mm photo, detailed atmospheric Bollywood lighting, photorealistic 8k",
      "image_prompt": "Cinematic photo of...",
      "narration": "Rich detailed Devanagari narrative paragraph (4-6 sentences, min 350 characters) showing the concrete event...",
      "dialogue": [
        {{
          "character": "Name",
          "acting_instruction": "Emotion/tone",
          "line": "Spoken line in natural Hindi without speaker labels",
          "gender": "male|female"
        }}
      ],
      "mood": "suspense|drama|emotional|confrontation",
      "characters_present": ["Name"],
      "sfx_hint": "door creaking, thunder, footsteps"
    }}
  ],
  "ending": "Complete concrete resolution showing the final fate of protagonist, antagonist, and mystery",
  "conclusion_moral": "Meaningful emotional realization emerging naturally from the true events",
  "call_to_action": "अगर आपको यह कहानी पसंद आई, तो वीडियो को लाइक करें और ऐसी ही रोमांचक कहानियों के लिए चैनल को सब्सक्राइब करें।"
}}"""

        for attempt in range(3):
            try:
                resp = self.llm.complete(prompt, system=system_prompt, json_mode=True)
                story_data = self.llm.parse_json(resp.text)
                if story_data and story_data.get("scenes"):
                    logger.info("Scene-based story writer successfully generated %d scenes", len(story_data["scenes"]))
                    return story_data
            except Exception as exc:
                logger.warning("Scene writer attempt %s failed: %s", attempt + 1, exc)

        logger.warning("All LLM scene writer attempts failed. Constructing procedural scene-based story.")
        return self._procedural_scene_story(blueprint, genre, category_name, target_scene_count, is_short)

    def _procedural_scene_story(
        self,
        blueprint: dict[str, Any],
        genre: str,
        category_name: str,
        target_scene_count: int,
        is_short: bool,
    ) -> dict[str, Any]:
        """
        Creates a concrete, fully articulated story with ZERO vague summaries
        and ZERO repetitive sentences.
        """
        main_char = blueprint.get("main_character", {})
        mc_name = main_char.get("name", "राहुल")
        mc_attire = main_char.get("signature_attire", "गहरे नीले रंग की जैकेट")

        antagonist = blueprint.get("antagonist_or_opposing_force", {})
        ant_name = antagonist.get("name", "चाचा कैलाश")

        title = f"{mc_name} और हवेली के वसीयतनामे का रहस्य"
        synopsis = (
            f"पिता की आकस्मिक मृत्यु के बाद {mc_name} के सामने जब पैतृक हवेली खाली करने का नोटिस आता है, "
            f"तो वह हार मानने के बजाय पिता के पुराने कमरे से उस 20 साल पुराने जाली दस्तावेज का सच बाहर लाता है।"
        )

        scenes = [
            {
                "scene_number": 1,
                "story_beat": "opening_hook",
                "duration_estimate_sec": 45,
                "visual_description": f"Cinematic 35mm photo of {mc_name} in dark navy jacket standing on porch of old Indian mansion in rain, confronting an older man in white kurta holding legal papers.",
                "image_prompt": f"Cinematic photo of {mc_name} confronting an older man holding legal documents outside an old Indian mansion, heavy rain, dramatic thriller lighting",
                "narration": (
                    f"{mc_name} उस शाम ऑफिस से लौटा तो हवेली के मुख्य दरवाजे पर {ant_name} हाथ में कुछ सरकारी कागजात लिए खड़े थे। "
                    f"बगल में खड़ी पीली बुलडोज़र का इंजन चालू था और ड्राइवर राहुल के घर की बाउंड्री वॉल नाप रहा था। "
                    f"{mc_name} ने आगे बढ़कर पूछा कि यह सब तमाशा किस लिए किया जा रहा है।"
                ),
                "dialogue": [
                    {
                        "character": ant_name,
                        "acting_instruction": "घमंड भरी आवाज में",
                        "line": f"यह तमाशा नहीं, कोर्ट का बेदखली नोटिस है। तुम्हारे पिता ने मरने से पहले यह हवेली मेरे पास चालीस लाख में गिरवी रखी थी।",
                        "gender": "male",
                    },
                    {
                        "character": mc_name,
                        "acting_instruction": "गुस्से और संयम से",
                        "line": "पिताजी कभी ऐसा नहीं कर सकते। मुझे चौबीस घंटे का वक्त दीजिए, मैं एक-एक कागज़ की जांच करूँगा।",
                        "gender": "male",
                    },
                ],
                "mood": "confrontation",
                "characters_present": [mc_name, ant_name],
                "sfx_hint": "bulldozer engine, rain, shouting",
            },
            {
                "scene_number": 2,
                "story_beat": "investigation",
                "duration_estimate_sec": 45,
                "visual_description": f"Interior of a vintage dusty study room in Indian haveli, {mc_name} examining a yellowed diary and old brass keys under a single desk lamp.",
                "image_prompt": f"Interior of vintage dusty study in Indian mansion, {mc_name} examining old handwritten diary under desk lamp, dramatic shadows",
                "narration": (
                    f"{mc_name} ने पिता के बंद अध्ययन कक्ष का ताला तोड़ा तो मेज पर धूल की मोटी परत जमी हुई थी। "
                    f"उसने किताबों की पुरानी रैक को खींचा तो उसके पीछे दीवार में जड़ा एक छोटा गुप्त लॉकर दिखाई दिया। "
                    f"लॉकर के अंदर पिता की 2018 की डायरी और एक बंद लिफाफा रखा था जिस पर 'अंतिम सच' लिखा हुआ था।"
                ),
                "dialogue": [
                    {
                        "character": mc_name,
                        "acting_instruction": "स्वयं से फुसफुसाते हुए",
                        "line": "पिताजी ने डायरी के हर पन्ने पर तारीख और समय दर्ज किया है... यहाँ कुछ बहुत बड़ा राज़ छुपा है।",
                        "gender": "male",
                    }
                ],
                "mood": "suspense",
                "characters_present": [mc_name],
                "sfx_hint": "creaking shelf, turning paper pages",
            },
            {
                "scene_number": 3,
                "story_beat": "clue_discovery",
                "duration_estimate_sec": 45,
                "visual_description": f"Macro close-up of {mc_name}'s hands holding a bank receipt and a legal stamp paper, magnifying glass highlighting discrepancy in license dates.",
                "image_prompt": "Close-up of hands examining vintage Indian stamp paper with magnifying glass, highlighting date discrepancy, intense dramatic lighting",
                "narration": (
                    f"डायरी के पन्नों में पिता ने लिखा था कि उन्होंने बैंक का पूरा कर्ज़ 2019 में ही चुकता कर दिया था। "
                    f"{mc_name} ने जब चाचा के दिए स्टैम्प पेपर को मैग्निफाइंग ग्लास से देखा, तो उसके होश उड़ गए। "
                    f"स्टैम्प पेपर पर तारीख 2018 की दर्ज थी, लेकिन उस पर छपे वेंडर का सरकारी लाइसेंस नंबर 2021 में जारी हुआ था।"
                ),
                "dialogue": [
                    {
                        "character": mc_name,
                        "acting_instruction": "दृढ़ निश्चय के साथ",
                        "line": "यह स्टैम्प पेपर बैक-डेट में खरीदा गया जाली दस्तावेज है। चाचा ने यह फर्जीवाड़ा खुद रचा है।",
                        "gender": "male",
                    }
                ],
                "mood": "discovery",
                "characters_present": [mc_name],
                "sfx_hint": "magnifying glass clink, sharp violin note",
            },
            {
                "scene_number": 4,
                "story_beat": "climax",
                "duration_estimate_sec": 45,
                "visual_description": f"Grand hall of the mansion during morning, {mc_name} presenting original bank documents to a police inspector while {ant_name} stands pale in shock.",
                "image_prompt": "Grand hall of Indian mansion, young man presenting documents to police inspector, older man in corner looking shocked and guilty, cinematic courtroom drama feel",
                "narration": (
                    f"अगली सुबह जब {ant_name} रजिस्ट्री के कागजात पर दस्तखत कराने आया, तो बरामदे में पुलिस इंस्पेक्टर शर्मा पहले से मौजूद थे। "
                    f"{mc_name} ने बैंक का ओरिजिनल नो-ड्यूज सर्टिफिकेट और फॉरेंसिक लैब की रिपोर्ट इंस्पेक्टर के हाथ में थमा दी। "
                    f"रिपोर्ट में साफ लिखा था कि स्टैम्प पेपर की स्याही सिर्फ छह महीने पुरानी है।"
                ),
                "dialogue": [
                    {
                        "character": mc_name,
                        "acting_instruction": "गंभीर और बुलंद आवाज में",
                        "line": f"चाचा जी, सट्टे के कर्ज़ को चुकाने के लिए आपने मरे हुए भाई की जाली वसीयत बनाई, लेकिन यह भूल गए कि सच हमेशा सुबूत छोड़ता है।",
                        "gender": "male",
                    },
                    {
                        "character": ant_name,
                        "acting_instruction": "हकलाते हुए",
                        "line": "यह सब झूठ है... यह लड़का मुझे फंसा रहा है!",
                        "gender": "male",
                    },
                ],
                "mood": "confrontation",
                "characters_present": [mc_name, ant_name],
                "sfx_hint": "handcuffs clicking, heavy footsteps",
            },
            {
                "scene_number": 5,
                "story_beat": "resolution",
                "duration_estimate_sec": 45,
                "visual_description": f"Sunlight streaming through tall open windows of the peaceful mansion, {mc_name} placing fresh marigold garland on father's framed portrait.",
                "image_prompt": "Warm golden morning sunlight through arched windows of ancestral Indian mansion, young man paying respects to father's photo with marigolds, emotional peaceful atmosphere",
                "narration": (
                    f"पुलिस {ant_name} और उसके जाली दस्तावेज बनाने वाले साथी को हथकड़ी लगाकर गाड़ी में बिठा चुकी थी। "
                    f"{mc_name} ने हवेली के मुख्य द्वार पर पिता के नाम की नेमप्लेट को कपड़े से पोंछकर दोबारा सीधा किया। "
                    f"कमरे की खिड़कियों से अंदर आती सुबह की सुनहरी धूप ने घर के हर कोने से बरसों पुराना भय मिटा दिया था।"
                ),
                "dialogue": [
                    {
                        "character": mc_name,
                        "acting_instruction": "नम आँखों से मुस्कुराते हुए",
                        "line": "पिताजी, आपकी सच्चाई और आपका घर आज हमेशा के लिए महफ़ूज़ हो गया।",
                        "gender": "male",
                    }
                ],
                "mood": "emotional",
                "characters_present": [mc_name],
                "sfx_hint": "gentle morning birds, peaceful soft flute",
            },
        ]

        if target_scene_count > 5:
            # Add intermediate concrete scenes if long-form is requested
            extra_scenes = [
                {
                    "scene_number": 3,
                    "story_beat": "bank_confrontation",
                    "duration_estimate_sec": 45,
                    "visual_description": f"{mc_name} at an old cooperative bank counter questioning a nervous bank clerk about archived loan ledgers.",
                    "image_prompt": f"{mc_name} confronting nervous bank clerk in old Indian cooperative bank, ledgers piled high, dramatic lighting",
                    "narration": (
                        f"{mc_name} सुबह 10 बजे जिला सहकारी बैंक की मुख्य शाखा पहुंचा और पिता के खाते की 2018 की लेजर बुक मांगी। "
                        f"बैंक क्लर्क पहले टालमटोल करने लगा, लेकिन जब राहुल ने कानूनी नोटिस का हवाला दिया तो क्लर्क ने पुराना बहीखाता निकाला। "
                        f"बहीखाते में दर्ज था कि चालीस लाख का कर्ज़ 14 दिसंबर 2019 को ड्राफ्ट संख्या 4402 से पूरी तरह चुकता हो चुका था।"
                    ),
                    "dialogue": [
                        {
                            "character": mc_name,
                            "acting_instruction": "दृढ़ता से",
                            "line": "इस ड्राफ्ट की सत्यापित प्रति मुझे अभी चाहिए, क्योंकि किसी की जिंदगी और घर दांव पर लगा है।",
                            "gender": "male",
                        }
                    ],
                    "mood": "suspense",
                    "characters_present": [mc_name],
                    "sfx_hint": "bank stamp thudding, paper rustle",
                },
                {
                    "scene_number": 4,
                    "story_beat": "vendor_interrogation",
                    "duration_estimate_sec": 45,
                    "visual_description": f"{mc_name} confronting a street-side stamp vendor in a bustling Indian court complex.",
                    "image_prompt": f"{mc_name} questioning nervous elderly notary vendor in Indian court alleyway, typewriters and files around, realistic cinematic drama",
                    "narration": (
                        f"कोर्ट परिसर की संकरी गली में राहुल ने उस स्टैम्प वेंडर को ढूंढ निकाला जिसके रजिस्टर में यह एंट्री थी। "
                        f"वेंडर ने राहुल के हाथ में बैंक का प्रमाण देखा तो उसके हाथ कांपने लगे। "
                        f"उसने कबूल किया कि कैलाश ने उसे पचास हज़ार रुपये देकर पुराना खाली स्टैम्प पेपर बैक-डेट में खरीदा था।"
                    ),
                    "dialogue": [
                        {
                            "character": mc_name,
                            "acting_instruction": "दबाव बनाते हुए",
                            "line": "अगर तुमने सच लिखकर नहीं दिया, तो अगली जेल तुम्हारी होगी। सच बताओ कैलाश ने तुम्हें कब पैसे दिए थे?",
                            "gender": "male",
                        }
                    ],
                    "mood": "tension",
                    "characters_present": [mc_name],
                    "sfx_hint": "court chatter, typewriter clatter",
                },
                {
                    "scene_number": 5,
                    "story_beat": "forensic_verification",
                    "duration_estimate_sec": 45,
                    "visual_description": f"{mc_name} receiving sealed forensic laboratory report from a senior scientist under clinical fluorescent lights.",
                    "image_prompt": f"{mc_name} receiving official sealed forensic document from scientist in laboratory setting, authentic Indian cinematic lighting",
                    "narration": (
                        f"दोपहर दो बजे राहुल फॉरेंसिक प्रयोगशाला पहुँचा और स्टैम्प पेपर की आधिकारिक केमिकल जांच रिपोर्ट हासिल की। "
                        f"वरिष्ठ वैज्ञानिक ने सीलबंद लिफाफा सौंपते हुए पुष्टि की कि कागज़ पर प्रयुक्त स्याही सिर्फ कुछ महीने पुरानी थी। "
                        f"इस अकाट्य सुबूत के हाथ आते ही कैलाश की पूरी झूठी कहानी एक ही पल में बिखर चुकी थी।"
                    ),
                    "dialogue": [
                        {
                            "character": mc_name,
                            "acting_instruction": "राहत की सांस लेते हुए",
                            "line": "अब कानून के सामने कोई बहाना नहीं चलेगा, दूध का दूध और पानी का पानी होकर रहेगा।",
                            "gender": "male",
                        }
                    ],
                    "mood": "relief",
                    "characters_present": [mc_name],
                    "sfx_hint": "paper seal tearing, dramatic brass chord",
                },
            ]
            # Insert and re-index scenes (giving 8 complete scenes)
            scenes.insert(2, extra_scenes[0])
            scenes.insert(3, extra_scenes[1])
            scenes.insert(4, extra_scenes[2])
            for idx, sc in enumerate(scenes):
                sc["scene_number"] = idx + 1

        ending = (
            f"अदालत ने {ant_name} की जाली वसीयत को निरस्त करते हुए {mc_name} के नाम हवेली का कानूनी मालिकाना हक बहाल कर दिया। "
            f"कैलाश और जाली वेंडर को तीन साल के सश्रम कारावास की सजा सुनाई गई, और {mc_name} के पिता की ईमानदारी पर लगा हर दाग हमेशा के लिए धुल गया।"
        )
        moral = "सच्चाई के दस्तावेज चाहे कितने भी पुराने बस्ते में बंद हों, जब साहस और ठोस सुबूतों के साथ लड़ाई लड़ी जाती है तो झूठ की हार तय होती है।"

        return {
            "title": title,
            "synopsis": synopsis,
            "characters": [
                {
                    "name": mc_name,
                    "gender": "male",
                    "age_group": "27 years old",
                    "description": f"Young Indian investigator with sharp jawline, intense eyes, wearing {mc_attire}",
                    "voice_id_hint": "hi_IN-pratham-medium",
                },
                {
                    "name": ant_name,
                    "gender": "male",
                    "age_group": "52 years old",
                    "description": "Cunning older Indian man in crisp white kurta with calculating eyes and thin mustache",
                    "voice_id_hint": "hi_IN-pratham-medium",
                },
            ],
            "character_references": [
                {
                    "name": mc_name,
                    "gender": "male",
                    "age_group": "27 years old",
                    "physical_appearance": f"Sharp natural Indian features, clean shaven, height 5'11, intense focused expression",
                    "signature_attire": mc_attire,
                    "personality": "Observant, emotionally grounded, determined",
                }
            ],
            "hook_opening": scenes[0]["narration"],
            "scenes": scenes,
            "ending": ending,
            "conclusion_moral": moral,
            "call_to_action": "अगर आपको यह कहानी पसंद आई, तो वीडियो को लाइक करें और ऐसी ही रोमांचक कहानियों के लिए चैनल को सब्सक्राइब करें।",
        }
