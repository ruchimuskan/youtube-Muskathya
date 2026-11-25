from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.ai.repetition_detector import RepetitionDetector
from app.ai.scene_based_story_writer import SceneBasedStoryWriter
from app.ai.story_blueprint_generator import StoryBlueprintGenerator
from app.ai.story_generator import StoryGenerationRequest, StoryGenerator
from app.ai.story_logic_validator import StoryLogicValidator
from app.ai.story_quality_auditor import StoryQualityAuditor
from app.ai.story_rewriter import StoryRewriter
from app.ai.vague_sentence_detector import VagueSentenceDetector


def test_vague_sentence_detector_flags_banned_empty_phrases():
    detector = VagueSentenceDetector()

    # Story containing bad vague summaries as identified in the user prompt
    bad_text = (
        "उसे जिंदगी में बहुत मुश्किलों का सामना करना पड़ा। "
        "उसकी परेशानियां बढ़ती चली गईं। "
        "हालात बहुत खराब हो गए। "
        "उसे कई समस्याओं से गुजरना पड़ा। "
        "परिवार पर दुखों का पहाड़ टूट पड़ा और उसकी जिंदगी बदल गई।"
    )
    findings = detector.scan_text(bad_text, location="narration", scene_number=1)

    assert len(findings) >= 4
    phrases_flagged = [f.phrase for f in findings]
    assert any("मुश्किलों का सामना" in p for p in phrases_flagged)
    assert any("परेशानियां बढ़ती" in p or "हालात बहुत खराब" in p for p in phrases_flagged)
    assert any("दुखों का पहाड़" in p or "जिंदगी बदल गई" in p for p in phrases_flagged)

    story_with_vague = {
        "title": "परीक्षण",
        "ending": "समय के साथ सब ठीक हो गया और इस तरह उसकी जिंदगी बदल गई।",
        "scenes": [
            {
                "scene_number": 1,
                "narration": bad_text,
                "dialogue": [{"character": "राहुल", "line": "किस्मत ने उसका साथ छोड़ दिया।"}],
            }
        ],
    }

    penalty, critiques = detector.calculate_vague_penalty(story_with_vague)
    assert penalty > 0
    assert len(critiques) >= 4
    assert any("vague phrase" in c.lower() for c in critiques)


def test_vague_sentence_detector_passes_concrete_event_story():
    detector = VagueSentenceDetector()

    # Good scene from user prompt: concrete event with who, where, what was said and done
    good_text = (
        "राहुल उस दिन शाम छह बजे ऑफिस से लौटा तो घर के बाहर उसके चाचा खड़े थे। "
        "उनके हाथ में सफेद रंग के कानूनी कागज थे। "
        "चाचा ने कागज उसके सामने करते हुए कहा कि यह मकान अब तुम्हारे नाम नहीं रहेगा। "
        "राहुल के हाथ कांपने लगे और उसने वसीयत पर पिता के दस्तखत की तारीख देखी।"
    )
    findings = detector.scan_text(good_text, location="narration", scene_number=1)
    assert len(findings) == 0


def test_repetition_detector_identifies_duplicate_and_generic_dialogues():
    detector = RepetitionDetector()

    story_with_repeats = {
        "title": "रिपीटेशन टेस्ट",
        "scenes": [
            {
                "scene_number": 1,
                "narration": "राघव ने पुराना लकड़ी का संदूक खोला। अंदर एक पीली डायरी रखी थी।",
                "dialogue": [{"character": "राघव", "line": "यह क्या है?"}],
            },
            {
                "scene_number": 2,
                "narration": "राघव ने पुराना लकड़ी का संदूक खोला। अंदर एक पीली डायरी रखी थी।",  # Identical narration
                "dialogue": [{"character": "राघव", "line": "यह क्या है?"}],  # Duplicate dialogue
            },
            {
                "scene_number": 3,
                "narration": "तहखाने के कोने में एक लोहे की जंजीर पड़ी थी।",
                "dialogue": [{"character": "राघव", "line": "तुम कौन हो?"}],  # Generic question
            },
        ],
    }

    findings = detector.detect_repetitions(story_with_repeats)
    assert len(findings) >= 2

    types = [f.type for f in findings]
    assert "duplicate_sentence" in types or "repeated_paragraph" in types
    assert "duplicate_dialogue" in types

    penalty, critiques = detector.calculate_repetition_penalty(story_with_repeats)
    assert penalty >= 10
    assert len(critiques) >= 2


def test_story_blueprint_generator_procedural_integrity():
    gen = StoryBlueprintGenerator()
    topic = {"main_topic": "पुश्तैनी हवेली का गुप्त वसीयतनामा", "angle": "चाचा की 20 साल पुरानी जाली वसीयत"}

    blueprint = gen._procedural_fallback_blueprint(
        genre="suspense_thriller",
        category_name="रहस्य",
        topic=topic,
        target_scene_count=8,
    )

    assert "central_concept" in blueprint
    assert "main_character" in blueprint
    assert blueprint["main_character"]["name"] == "राहुल"
    assert "supporting_characters" in blueprint
    assert len(blueprint["supporting_characters"]) >= 2
    assert "main_conflict" in blueprint
    assert "what_happened" in blueprint["main_conflict"]
    assert "who_caused_it" in blueprint["main_conflict"]
    assert "hidden_clues" in blueprint
    assert len(blueprint["hidden_clues"]) >= 2
    assert "major_twist" in blueprint
    assert "climax" in blueprint
    assert "final_resolution" in blueprint
    assert "what_happened_to_main_character" in blueprint["final_resolution"]
    assert "what_happened_to_antagonist" in blueprint["final_resolution"]


def test_story_logic_validator_detects_sudden_unexplained_character():
    validator = StoryLogicValidator()

    # Story where character suddenly appears in climax with no prior setup
    story = {
        "title": "रहस्य",
        "characters": [{"name": "रोहन", "gender": "male"}],
        "ending": "सच्चाई सामने आ गई और हवेली शांत हो गई।",
        "scenes": [
            {
                "scene_number": i,
                "narration": f"रोहन दृश्य {i} में तहखाने की जांच कर रहा है।",
                "dialogue": [{"character": "रोहन", "line": "यहाँ कोई सुबूत होना चाहिए।"}],
            }
            for i in range(1, 8)
        ],
    }
    # Scene 8 introduces an unheralded stranger "अज्ञात तांत्रिक" who solves everything
    story["scenes"].append(
        {
            "scene_number": 8,
            "narration": "अचानक अज्ञात तांत्रिक ने आकर सारा रहस्य सुलझा दिया।",
            "dialogue": [{"character": "अज्ञात_तांत्रिक", "line": "यह सब मैंने किया था!"}],
        }
    )

    report = validator.validate(story)
    assert report.is_valid is False
    assert report.critical_count >= 1
    assert any("suddenly appears" in iss.description for iss in report.issues)


def test_story_quality_auditor_penalizes_vague_and_repetitive_story():
    auditor = StoryQualityAuditor()

    # A story packed with vague clichés and repeated sentences
    vague_repetitive_story = {
        "title": "खराब कहानी",
        "synopsis": "उसकी जिंदगी बदल गई।",
        "ending": "समय के साथ सब ठीक हो गया।",
        "conclusion_moral": "यही जिंदगी की सच्चाई है।",
        "characters": [{"name": "अमित", "gender": "male"}],
        "scenes": [
            {
                "scene_number": 1,
                "narration": "उसे बहुत संघर्ष करना पड़ा। उसके हालात बहुत खराब हो गए थे। परिवार पर दुखों का पहाड़ टूट पड़ा।",
                "dialogue": [{"character": "अमित", "line": "यह क्या है?"}],
            },
            {
                "scene_number": 2,
                "narration": "उसे बहुत संघर्ष करना पड़ा। उसके हालात बहुत खराब हो गए थे। परिवार पर दुखों का पहाड़ टूट पड़ा।",
                "dialogue": [{"character": "अमित", "line": "यह क्या है?"}],
            },
            {
                "scene_number": 3,
                "narration": "उसने बहुत कुछ सहा और किस्मत ने उसका साथ छोड़ दिया।",
                "dialogue": [{"character": "अमित", "line": "यह क्या हो रहा है?"}],
            },
            {
                "scene_number": 4,
                "narration": "सब कुछ बदल चुका था और जीवन में बड़ा बदलाव आ गया।",
                "dialogue": [{"character": "अमित", "line": "तुम कौन हो?"}],
            },
        ],
    }

    report = auditor.audit(vague_repetitive_story)

    # Must fail validation!
    assert report.passed is False
    assert report.repetition_penalty > 0
    assert report.vague_penalty > 0
    assert report.total_score < 85
    assert len(report.critical_issues) > 0
    assert "VAGUE TELLING-NOT-SHOWING" in report.feedback_for_rewrite or "REPETITION" in report.feedback_for_rewrite


def test_scene_based_story_writer_procedural_story_has_full_events():
    writer = SceneBasedStoryWriter()
    blueprint_gen = StoryBlueprintGenerator()

    topic = {"main_topic": "पुरानी हवेली के वसीयतनामे का रहस्य"}
    blueprint = blueprint_gen._procedural_fallback_blueprint("mystery", "रहस्य", topic, 8)

    story = writer._procedural_scene_story(blueprint, "mystery", "रहस्य", 8, is_short=False)

    assert len(story["scenes"]) >= 8
    assert "रहस्य" in story["title"]
    assert len(story["ending"]) >= 100

    # Ensure every scene has concrete narration and dialogue without generic filler
    for sc in story["scenes"]:
        narr = sc["narration"]
        assert len(narr) >= 120
        # Check no banned phrases
        assert "उसे बहुत संघर्ष करना पड़ा" not in narr
        assert "जिंदगी बदल गई" not in narr
        assert "दुखों का पहाड़" not in narr
        # Dialogue checks
        assert len(sc["dialogue"]) >= 1
        for d in sc["dialogue"]:
            assert d["line"] != "यह क्या है?"
            assert d["line"] != "यह क्या हो रहा है?"


def test_story_generator_end_to_end_procedural_fallback():
    mock_llm = MagicMock()
    mock_llm.complete.side_effect = RuntimeError("Simulated API failure")

    gen = StoryGenerator(llm=mock_llm)
    req = StoryGenerationRequest(
        language="hi",
        genre="suspense_thriller",
        target_duration_sec=360,
        is_short=False,
        category_id="suspense_thriller",
    )

    story = gen.generate(req)

    assert story is not None
    assert len(story["scenes"]) >= 8
    assert story["blueprint"] is not None
    assert story["quality_score"] >= 80

    # Check that ending is not a cop-out
    ending = story["ending"]
    assert "सब ठीक हो गया" not in ending
    assert len(ending) > 80

    # Verify no vague phrases in generated scenes
    detector = VagueSentenceDetector()
    findings = detector.audit_story(story)
    assert len(findings) == 0, f"Found unexpected vague phrases in procedural story: {findings}"
