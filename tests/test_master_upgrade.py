from pathlib import Path
from unittest.mock import MagicMock
from app.ai.story_generator import StoryGenerator
from app.ai.story_quality_checker import StoryQualityChecker
from app.creative.hindi_thumbnail_copy import derive_story_curiosity_hook, enforce_short_headline
from app.images.character_manager import CharacterManager
from app.video.quality_checker import QualityChecker


def test_dialogue_cleaning_removes_labels_and_brackets():
    """Verify actor directions and colon prefixes are never read aloud by TTS."""
    raw = "मां (घबराकर): रोहित! तुम इतनी देर कहां थे?"
    char, emo, line = StoryGenerator.clean_dialogue_line(raw, default_char="मां")
    assert char == "मां"
    assert emo == "घबराकर"
    assert line == "रोहित! तुम इतनी देर कहां थे?"
    assert "(" not in line
    assert ":" not in line

    raw2 = "(रोते हुए) मुझे माफ़ कर दो।"
    char2, emo2, line2 = StoryGenerator.clean_dialogue_line(raw2, default_char="राघव")
    assert emo2 == "रोते हुए"
    assert line2 == "मुझे माफ़ कर दो।"


def test_story_quality_checker_scores_and_validates():
    """Verify the 10-dimension story quality checker flags weak stories and passes complete stories."""
    checker = StoryQualityChecker()
    # Mock LLM to return a solid 88 score
    checker._evaluate_with_llm = MagicMock(return_value={
        "scores": {
            "opening_hook": 9,
            "character_consistency": 9,
            "plot_logic_continuity": 9,
            "suspense_escalation": 8,
            "emotional_engagement": 9,
            "twist_quality": 9,
            "climax_impact": 9,
            "ending_completeness": 9,
            "hindi_grammar_dialogue": 9,
            "anti_repetition": 9,
        },
        "total_score": 89,
        "feedback": "Strong Bollywood suspense structure."
    })

    good_story = {
        "title": "हवेली का खौफ़नाक सच",
        "synopsis": "एक बंद तहखाने का राज जो बीस साल बाद खुला।",
        "hook_opening": "रात के बारह बजे पुरानी हवेली से चीखें आने लगीं...",
        "ending": "राघव ने उस खत को आग में जला दिया और बीस साल पुराना खौफ़ हमेशा के लिए खत्म हो गया।",
        "conclusion_moral": "सच्चाई को चाहे कितना भी छुपा लो, अंत में जीत सच की ही होती है।",
        "characters": [
            {"name": "राघव", "gender": "male", "description": "Intense investigator"}
        ],
        "character_references": [
            {"name": "राघव", "gender": "male", "physical_appearance": "Sharp Indian features"}
        ],
        "scenes": [
            {
                "scene_number": i,
                "story_beat": "suspense",
                "narration": f"दृश्य {i}: हवेली के चारों तरफ गहरा सन्नाटा पसरा हुआ था और दिल की धड़कनें साफ़ सुनाई दे रही थीं। राघव ने जैसे ही पुराने दरवाज़े को धक्का दिया, अंदर की ठंडी हवा ने उसके रोंगटे खड़े कर दिए। धूल भरी सीढ़ियों पर ताज़ा कदमों के निशान साफ़ दिखाई दे रहे थे, जिससे साबित होता था कि कोई यहाँ हाल ही में आया था।",
                "dialogue": [{"character": "राघव", "line": f"कोई है यहाँ पर? सामने आओ, दृश्य {i}!"}],
            }
            for i in range(1, 16)
        ]
    }

    report = checker.evaluate(good_story)
    assert report.total_score >= 85
    assert report.passed is True
    assert "opening_hook" in report.dimensions


def test_character_manager_deterministic_seeds_and_sheet():
    """Verify character consistency seeds are deterministic and profiles are extracted."""
    story = {
        "story_project_id": 999,
        "characters": [
            {"name": "राघव", "gender": "male", "age_group": "28 years", "description": "Leather jacket, intense gaze"},
            {"name": "प्रिया", "gender": "female", "age_group": "25 years", "description": "Traditional saree, fearful eyes"},
        ]
    }
    mgr1 = CharacterManager(story)
    mgr2 = CharacterManager(story)

    seed1 = mgr1.character_seed("राघव", 999)
    seed2 = mgr2.character_seed("राघव", 999)
    assert seed1 == seed2

    sheet = mgr1.export_character_sheet()
    assert len(sheet) == 2
    assert sheet[0]["name"] == "राघव"

    scene = {
        "visual_description": "Entering a dark basement",
        "dialogue": [{"character": "राघव", "line": "दरवाजा बंद है!"}]
    }
    prompt = mgr1.scene_prompt(scene)
    assert "राघव" in prompt
    assert "ultra-realistic cinematic photography" in prompt


def test_thumbnail_curiosity_hooks():
    """Verify thumbnail hooks are 2 to 5 words and extract high curiosity."""
    story_with_letter = {
        "title": "गाँव की हवेली",
        "synopsis": "एक पुराने खत में छुपा था बीस साल पुराना खौफ़।",
    }
    hook = derive_story_curiosity_hook(story_with_letter)
    assert len(hook.split()) <= 5
    assert "खत" in hook or "सच" in hook

    short = enforce_short_headline("यह एक बहुत ही लंबी हेडलाइन है जो मोबाइल पर अच्छी नहीं दिखेगी", max_words=5)
    assert len(short.split()) == 5


def test_quality_checker_17_point_checklist():
    """Verify QualityChecker validates the comprehensive Bollywood pre-upload checklist."""
    qc = QualityChecker()
    # Mock probe
    qc._ffprobe = MagicMock(return_value={
        "format": {"duration": "650.0"},
        "streams": [
            {"codec_type": "video", "width": 1920, "height": 1080},
            {"codec_type": "audio"},
        ]
    })

    dummy_video = Path("/tmp/test_vid.mp4")
    dummy_video.write_bytes(b"dummy_data")
    dummy_thumb = Path("/tmp/test_thumb.png")
    from PIL import Image
    Image.new("RGB", (1280, 720), (20, 20, 20)).save(dummy_thumb)

    story = {
        "quality_score": 90,
        "hook_opening": "आधी रात का रहस्य...",
        "ending": "सच्चाई सामने आ गई।",
        "conclusion_moral": "सत्यमेव जयते।",
        "character_references": [{"name": "नायक"}],
        "scenes": [{"scene_number": i} for i in range(1, 16)],
    }
    seo = {
        "recommended_title": "हवेली का सच",
        "description": "रहस्यमयी कहानी",
        "tags": ["mystery", "hindi story"],
    }
    image_paths = [Path(f"/tmp/scene_{i}.png") for i in range(15)]

    res = qc.inspect_video(
        dummy_video,
        expected_aspect="16:9",
        min_duration=600,
        max_duration=900,
        thumbnail_path=dummy_thumb,
        title="हवेली का सच",
        story_complete=True,
        language="hi",
        story=story,
        seo=seo,
        image_paths=image_paths,
    )
    assert res.passed is True
    check_names = {c["name"] for c in res.checks}
    assert "story_quality_score" in check_names
    assert "images_match_scenes" in check_names
    assert "seo_metadata_generated" in check_names
