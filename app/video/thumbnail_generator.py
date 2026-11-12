from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

logger = logging.getLogger(__name__)

YOUTUBE_THUMB_SIZE = (1280, 720)


class ThumbnailGenerator:
    def _hindi_font(self, size: int) -> ImageFont.ImageFont:
        candidates = [
            "/System/Library/Fonts/Supplemental/NotoSansDevanagari-Bold.ttf",
            "/System/Library/Fonts/KohinoorDevanagari-Bold.ttf",
            "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        ]
        for path in candidates:
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
        return ImageFont.load_default()

    def generate_variants(
        self,
        base_image: Path,
        title: str,
        output_dir: Path,
        count: int = 3,
    ) -> list[Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        variants: list[Path] = []

        with Image.open(base_image) as src:
            base = src.convert("RGB").resize(YOUTUBE_THUMB_SIZE, Image.Resampling.LANCZOS)

        for i in range(count):
            img = base.copy()
            overlay = Image.new("RGBA", YOUTUBE_THUMB_SIZE, (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)
            bar_height = 180 if i == 0 else 140
            draw.rectangle(
                [(0, YOUTUBE_THUMB_SIZE[1] - bar_height), (1280, 720)],
                fill=(0, 0, 0, 170 if i < 2 else 120),
            )
            img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

            draw = ImageDraw.Draw(img)
            font_size = 64 if i == 0 else 52
            font = self._hindi_font(font_size)
            text = title[:36]
            tw = draw.textlength(text, font=font) if hasattr(draw, "textlength") else len(text) * 20
            x = max((1280 - int(tw)) // 2, 20)
            y = 720 - bar_height + 30
            draw.text((x + 2, y + 2), text, fill=(0, 0, 0), font=font)
            draw.text((x, y), text, fill=(255, 255, 255), font=font)

            if i == 1:
                img = ImageEnhance.Contrast(img).enhance(1.15)

            out = output_dir / f"thumb_v{i + 1}.jpg"
            img.save(out, quality=92)
            variants.append(out)

        return variants

    def pick_best(self, variants: list[Path]) -> Path:
        scores: list[tuple[float, Path]] = []
        for p in variants:
            with Image.open(p) as im:
                im = im.convert("L")
                # contrast proxy via std dev
                hist = im.histogram()
                total = sum(hist)
                mean = sum(i * h for i, h in enumerate(hist)) / max(total, 1)
                var = sum(((i - mean) ** 2) * h for i, h in enumerate(hist)) / max(total, 1)
                scores.append((var**0.5, p))
        scores.sort(reverse=True)
        return scores[0][1]
