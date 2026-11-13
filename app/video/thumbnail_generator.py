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

    def _wrap_text(self, text: str, font: ImageFont.ImageFont, draw: ImageDraw.ImageDraw, max_w: int) -> list[str]:
        words = text.split()
        if not words:
            return [text[:28]]
        lines: list[str] = []
        current = words[0]
        for word in words[1:]:
            trial = f"{current} {word}"
            w = draw.textlength(trial, font=font) if hasattr(draw, "textlength") else len(trial) * 18
            if w <= max_w:
                current = trial
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return lines[:2]

    def _draw_outlined(
        self, draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, font: ImageFont.ImageFont
    ) -> None:
        x, y = xy
        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2), (-2, -2), (2, 2)):
            draw.text((x + dx, y + dy), text, fill=(0, 0, 0), font=font)
        draw.text((x, y), text, fill=(255, 245, 120), font=font)

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
            draw.rectangle([(0, 0), (1280, 140)], fill=(0, 0, 0, 90))
            bar_height = 200 if i == 0 else 165
            draw.rectangle(
                [(0, YOUTUBE_THUMB_SIZE[1] - bar_height), (1280, 720)],
                fill=(0, 0, 0, 200 if i < 2 else 165),
            )
            img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

            draw = ImageDraw.Draw(img)
            font_size = 76 if i == 0 else 60
            font = self._hindi_font(font_size)
            text = title.strip()[:42]
            lines = self._wrap_text(text, font, draw, 1180)
            line_h = font_size + 14
            total_h = len(lines) * line_h
            y0 = 720 - bar_height + max((bar_height - total_h) // 2, 24)
            for j, line in enumerate(lines):
                tw = draw.textlength(line, font=font) if hasattr(draw, "textlength") else len(line) * 22
                x = max((1280 - int(tw)) // 2, 24)
                self._draw_outlined(draw, (x, y0 + j * line_h), line, font)

            if i == 1:
                img = ImageEnhance.Contrast(img).enhance(1.12)

            out = output_dir / f"thumb_v{i + 1}.jpg"
            img.save(out, quality=94)
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
