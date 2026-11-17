import pytest
from app.ai.story_generator import StoryGenerator


def test_story_generator_deduplicates_repetitive_dialogues():
    gen = StoryGenerator()
    story = {
        "title": "परीक्षण कहानी",
        "synopsis": "एक रहस्यमयी घटना",
        "scenes": [
            {
                "scene_number": 1,
                "narration": "रोहन ने पुरानी हवेली का भारी लकड़ी का दरवाज़ा धीरे से धक्का देकर खोला।",
                "dialogue": [{"character": "रोहन", "line": "यह क्या है?", "gender": "male"}],
                "mood": "suspense",
            },
            {
                "scene_number": 2,
                "narration": "अंदर धूल से भरी मेज़ पर एक लाल डायरी रखी हुई थी।",
                "dialogue": [{"character": "रोहन", "line": "यह क्या है?", "gender": "male"}],
                "mood": "suspense",
            },
            {
                "scene_number": 3,
                "narration": "अचानक पीछे से किसी के भारी कदमों की आहट सुनाई दी।",
                "dialogue": [{"character": "रोहन", "line": "यह क्या हो रहा है?", "gender": "male"}],
                "mood": "suspense",
            },
            {
                "scene_number": 4,
                "narration": "अंधेरे से एक अजनबी चेहरा निकलकर सामने आया।",
                "dialogue": [{"character": "रोहन", "line": "यह क्या हो रहा है?", "gender": "male"}],
                "mood": "suspense",
            },
        ],
    }

    cleaned = gen._clean_and_deduplicate(story)
    lines = [d["line"] for sc in cleaned["scenes"] for d in sc.get("dialogue", [])]

    # All dialogue lines must now be unique!
    assert len(lines) == len(set(lines)), f"Found duplicate dialogues: {lines}"
    # The first 'यह क्या है?' is preserved, but subsequent duplicates are replaced
    assert lines[0] == "यह क्या है?"
    assert lines[1] != "यह क्या है?"
    assert lines[2] == "यह क्या हो रहा है?"
    assert lines[3] != "यह क्या हो रहा है?"


def test_story_generator_enriches_short_narration_stubs():
    gen = StoryGenerator()
    story = {
        "title": "परीक्षण कहानी",
        "scenes": [
            {
                "scene_number": 1,
                "narration": "रोहन ने चाबी उठाई।",  # Very short stub (18 chars)
                "dialogue": [],
                "mood": "suspense",
            }
        ],
    }
    cleaned = gen._clean_and_deduplicate(story)
    narr = cleaned["scenes"][0]["narration"]
    assert len(narr) >= 100, f"Narration stub was not enriched: {narr}"
    assert "रोहन ने चाबी उठाई।" in narr


def test_calculate_spoken_chars():
    gen = StoryGenerator()
    story = {
        "scenes": [
            {
                "scene_number": 1,
                "narration": "एक दो तीन चार पाँच",
                "dialogue": [{"line": "छह सात आठ"}],
            }
        ]
    }
    chars = gen._calculate_spoken_chars(story)
    assert chars == len("एक दो तीन चार पाँच") + len("छह सात आठ")
