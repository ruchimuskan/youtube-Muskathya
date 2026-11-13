from __future__ import annotations

from PIL import Image, ImageFilter


def strip_baked_text_regions(img: Image.Image) -> Image.Image:
    """Blur lower band where SDXL often hallucinates Hindi/English text."""
    img = img.convert("RGB")
    w, h = img.size
    band_top = int(h * 0.62)
    lower = img.crop((0, band_top, w, h))
    lower = lower.filter(ImageFilter.GaussianBlur(radius=14))
    img.paste(lower, (0, band_top))
    return img
