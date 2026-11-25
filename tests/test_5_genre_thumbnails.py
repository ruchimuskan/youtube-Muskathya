from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from app.creative.story_thumbnail_analyzer import StoryThumbnailAnalyzer, GENRE_VISUAL_PROFILES
from app.creative.thumbnail_engine import ThumbnailEngine
from app.video.thumbnail_generator import ThumbnailGenerator


GENRE_TEST_CASES = [
    {
        "genre": "mystery",
        "category_id": "village_life",
        "story": {
            "title": "पुरानी हवेली का रहस्य",
            "genre": "mystery",
            "characters": [{"name": "रघु", "description": "28-year-old brave villager in traditional kurta holding a lantern"}],
            "scenes": [
                {"scene_number": 1, "narration": "रात के घने अंधेरे में रघु पुरानी हवेली की तरफ बढ़ा जहां सालों से कोई नहीं गया था।"}
            ],
        },
    },
    {
        "genre": "family",
        "category_id": "emotional_family",
        "story": {
            "title": "टूटा हुआ भरोसा",
            "genre": "family",
            "characters": [{"name": "रिया", "description": "24-year-old daughter with teary eyes wearing a salwar kameez"}],
            "scenes": [
                {"scene_number": 1, "narration": "जब रिया ने अलमारी से वो वसीयत निकाली तो उसके पैरों तले जमीन खिसक गई।"}
            ],
        },
    },
    {
        "genre": "suspense",
        "category_id": "suspense_thriller",
        "story": {
            "title": "आखिरी कॉल का सच",
            "genre": "suspense",
            "characters": [{"name": "विक्रम", "description": "35-year-old intense detective in dark trench coat"}],
            "scenes": [
                {"scene_number": 1, "narration": "रात के ठीक दो बजे पुलिस स्टेशन का फोन बजा और विक्रम के होश उड़ गए।"}
            ],
        },
    },
    {
        "genre": "horror",
        "category_id": "horror_mystery",
        "story": {
            "title": "चीखती रात का खौफ़",
            "genre": "horror",
            "characters": [{"name": "अमित", "description": "30-year-old terrified traveler drenched in rain"}],
            "scenes": [
                {"scene_number": 1, "narration": "जंगल के बीचो-बीच उस खंडहर से अचानक किसी के रोने की भयानक आवाज आने लगी।"}
            ],
        },
    },
    {
        "genre": "motivational",
        "category_id": "inspirational",
        "story": {
            "title": "संघर्ष से शिखर तक",
            "genre": "motivational",
            "characters": [{"name": "संदीप", "description": "22-year-old determined athlete with sweat on forehead"}],
            "scenes": [
                {"scene_number": 1, "narration": "सबने कहा था कि वो कभी दौड़ नहीं पाएगा लेकिन संदीप ने हार मानना नहीं सीखा था।"}
            ],
        },
    },
]


def test_genre_visual_profiles_complete():
    for g in ["suspense", "mystery", "horror", "emotional", "family", "thriller", "motivational"]:
        assert g in GENRE_VISUAL_PROFILES
        assert "lighting" in GENRE_VISUAL_PROFILES[g]
        assert "atmosphere" in GENRE_VISUAL_PROFILES[g]
        assert "color_palette" in GENRE_VISUAL_PROFILES[g]


def test_analyzer_builds_genre_prompts():
    mock_llm = MagicMock()
    mock_llm.parse_json.side_effect = RuntimeError("offline")
    analyzer = StoryThumbnailAnalyzer(mock_llm)
    for tc in GENRE_TEST_CASES:
        analysis = analyzer.analyze(tc["story"], tc["category_id"])
        prompt = analysis.get("art_prompt_en")
        assert prompt is not None
        assert "Bollywood movie poster" in prompt
        assert "ABSOLUTELY NO TEXT" in prompt
        # Check that proper genre lighting or atmosphere is reflected
        profile = GENRE_VISUAL_PROFILES[tc["genre"]]
        assert any(k in prompt for k in profile["lighting"].split()[:3])


def test_thumbnail_engine_5_genres(tmp_path: Path):
    mock_llm = MagicMock()
    mock_llm.parse_json.side_effect = RuntimeError("offline")
    engine = ThumbnailEngine(llm=mock_llm)
    engine.openai_images = MagicMock()
    engine.openai_images.is_available.return_value = False
    engine.images = MagicMock()
    engine.images.is_available.return_value = False

    for tc in GENRE_TEST_CASES:
        out_dir = tmp_path / tc["genre"]
        variants, concepts, best = engine.generate(
            tc["story"],
            tc["category_id"],
            None,
            out_dir,
            count=1,
        )
        assert len(variants) >= 1
        assert best.exists()
        assert best.stat().st_size > 5000

        with Image.open(best) as img:
            assert img.size == (1280, 720)
