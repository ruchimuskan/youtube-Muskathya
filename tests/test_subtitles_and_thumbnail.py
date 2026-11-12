from pathlib import Path

from app.video.subtitle_generator import SubtitleGenerator
from app.video.thumbnail_generator import ThumbnailGenerator
from PIL import Image


def test_srt_generation(tmp_path):
    story = {
        "scenes": [
            {"scene_number": 1, "narration": "Hello world", "dialogue": []},
        ]
    }
    srt = SubtitleGenerator().build_from_story(
        story, [(1, 2.5)], tmp_path / "sub.srt", use_ass=False
    )
    text = srt.read_text(encoding="utf-8")
    assert "Hello world" in text
    assert "-->" in text


def test_thumbnail_variants(tmp_path):
    base = tmp_path / "base.png"
    Image.new("RGB", (800, 600), (100, 120, 180)).save(base)
    gen = ThumbnailGenerator()
    variants = gen.generate_variants(base, "Test Title", tmp_path / "thumbs", count=2)
    assert len(variants) == 2
    best = gen.pick_best(variants)
    assert best.exists()
