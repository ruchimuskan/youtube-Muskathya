from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps


def pick_hero_scene(images: list[Path]) -> Path:
    """Prefer a mid/climax frame (larger file ≈ richer SDXL output)."""
    if not images:
        raise ValueError("No scene images")
    if len(images) >= 3:
        candidates = images[1:-1] or images
    else:
        candidates = images
    return max(candidates, key=lambda p: p.stat().st_size if p.exists() else 0)


def enhance_scene_for_thumb(path: Path, out: Path) -> Path:
    """Boost contrast/saturation and center-crop for 16:9 thumbnail punch."""
    out.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(path) as src:
        im = ImageOps.exif_transpose(src.convert("RGB"))
        im = ImageOps.fit(im, (1280, 720), method=Image.Resampling.LANCZOS, centering=(0.5, 0.45))
        im = ImageEnhance.Contrast(im).enhance(1.22)
        im = ImageEnhance.Color(im).enhance(1.18)
        im = ImageEnhance.Sharpness(im).enhance(1.35)
        im = im.filter(ImageFilter.UnsharpMask(radius=2, percent=140, threshold=3))
        im.save(out, quality=94)
    return out
