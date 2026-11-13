from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance

from app.utils.devanagari_render import (
    devanagari_font_path,
    draw_devanagari_outlined,
    shaped_text_width,
)

logger = logging.getLogger(__name__)

YOUTUBE_THUMB_SIZE = (1280, 720)

TEXT_PALETTE = {
    "gold": (255, 215, 80),
    "white": (255, 255, 255),
    "red": (255, 70, 70),
}


class ThumbnailGenerator:
    def _baseline_y(self, top_y: int, size_px: int) -> int:
        """Map legacy top anchor (Pillow) to FreeType baseline."""
        return top_y + int(size_px * 0.82)

    def apply_story_overlay(
        self,
        base_image: Path,
        headline: str,
        output_path: Path,
        *,
        suspense: str = "",
        text_scheme: str = "gold",
    ) -> Path:
        """Hindi typography on lower third — keeps upper area for faces."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fill = TEXT_PALETTE.get(text_scheme, TEXT_PALETTE["gold"])

        headline = headline.strip()[:48]
        suspense = suspense.strip()[:36]

        with Image.open(base_image) as src:
            img = src.convert("RGB").resize(YOUTUBE_THUMB_SIZE, Image.Resampling.LANCZOS)

        overlay = Image.new("RGBA", YOUTUBE_THUMB_SIZE, (0, 0, 0, 0))
        draw_o = ImageDraw.Draw(overlay)
        bar_h = 220 if suspense else 190
        draw_o.rectangle(
            [(0, YOUTUBE_THUMB_SIZE[1] - bar_h), (1280, 720)],
            fill=(0, 0, 0, 255),
        )
        img = Image.alpha_composite(img.convert("RGBA"), overlay)
        font_path = devanagari_font_path()

        head_size = 78
        words = headline.split()
        if len(words) > 7:
            headline = " ".join(words[:7])
        tw = shaped_text_width(headline, font_path, head_size)
        hx = max((1280 - int(tw)) // 2, 20)
        hy_top = 720 - bar_h + 35
        draw_devanagari_outlined(
            img,
            (hx, self._baseline_y(hy_top, head_size)),
            headline,
            head_size,
            fill,
            font_path=font_path,
        )

        if suspense:
            sub_size = 48
            sw = shaped_text_width(suspense, font_path, sub_size)
            sx = max((1280 - int(sw)) // 2, 20)
            draw_devanagari_outlined(
                img,
                (sx, self._baseline_y(hy_top + 92, sub_size)),
                suspense,
                sub_size,
                TEXT_PALETTE["white"],
                font_path=font_path,
            )

        img = ImageEnhance.Contrast(img.convert("RGB")).enhance(1.08)
        img.save(output_path, quality=95)
        return output_path

    def generate_variants(
        self,
        base_image: Path,
        title: str,
        output_dir: Path,
        count: int = 3,
    ) -> list[Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        variants: list[Path] = []
        for i in range(count):
            out = output_dir / f"thumb_v{i + 1}.jpg"
            scheme = ("gold", "white", "red")[i % 3]
            self.apply_story_overlay(base_image, title, out, text_scheme=scheme)
            variants.append(out)
        return variants

    def pick_best(self, variants: list[Path]) -> Path:
        return variants[0] if variants else Path()
