from pathlib import Path

from PIL import Image

from app.creative.thumbnail_qc import validate_thumbnail


def test_thumbnail_qc_size(tmp_path: Path):
    p = tmp_path / "t.jpg"
    im = Image.new("RGB", (1280, 720))
    px = im.load()
    for y in range(720):
        for x in range(1280):
            px[x, y] = (80 + (x % 180), 60 + (y % 140), 90)
    im.save(p, quality=95)
    r = validate_thumbnail(p, analysis={"hindi_headline": "शिव जी का उपहार"})
    assert r.passed
