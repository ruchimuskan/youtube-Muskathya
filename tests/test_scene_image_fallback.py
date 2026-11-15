from pathlib import Path
from unittest.mock import MagicMock
from app.images.image_generator import ImageGenerator
from app.images.image_validator import is_valid_scene_image

def test_scene_image_fallback_resilience(tmp_path: Path):
    gen = ImageGenerator()
    # Mock Cloudflare as unavailable to test full fallback
    gen.cf_images.is_available = MagicMock(return_value=False)
    gen._comfy_available = MagicMock(return_value=False)

    story = {
        "title": "परीक्षण कहानी",
        "content_category_id": "moral",
        "scenes": [
            {"scene_number": 1, "narration": "दृश्य 1"},
            {"scene_number": 2, "narration": "दृश्य 2"},
            {"scene_number": 3, "narration": "दृश्य 3"},
        ]
    }

    out_dir = tmp_path / "images"
    paths, prompts = gen.generate_scene_images(story, out_dir, aspect_ratio="16:9")

    assert len(paths) == 3
    for p in paths:
        assert p.exists()
        assert is_valid_scene_image(p)
