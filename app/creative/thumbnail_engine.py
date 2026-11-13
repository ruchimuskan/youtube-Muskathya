from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any

from PIL import Image, ImageEnhance

from app.ai.providers import LLMRouter
from app.content.categories import get_category
from app.images.cloudflare_image import CloudflareImageGenerator
from app.creative.thumbnail_scene import enhance_scene_for_thumb, pick_hero_scene
from app.video.thumbnail_generator import ThumbnailGenerator

logger = logging.getLogger(__name__)
YOUTUBE_THUMB_SIZE = (1280, 720)


class ThumbnailEngine:
    """AI artwork without text + reliable Hindi overlay."""

    def __init__(self, llm: LLMRouter | None = None) -> None:
        self.llm = llm or LLMRouter()
        self.overlay = ThumbnailGenerator()
        self.images = CloudflareImageGenerator()

    def _concept_prompt(self, story: dict, category_id: str, variant: int) -> dict[str, Any]:
        category = get_category(category_id)
        prompt = f"""Analyze this Hindi story for YouTube thumbnail variant {variant + 1}.
Category: {category.name_hi}
Title: {story.get("title")}
Synopsis: {story.get("synopsis")}
Hook: {story.get("hook_opening")}

JSON only:
{{
  "focal_moment": "...",
  "main_character_emotion": "...",
  "art_prompt_en": "YouTube thumbnail, extreme close-up face or hero moment, dramatic rim light, vibrant colors, shallow depth of field, {category.thumbnail_tone}, Indian cinematic",
  "hindi_text": "2-5 powerful Hindi words for thumbnail",
  "composition": "close-up|wide|dramatic angle",
  "reason": "why this works for audience"
}}"""
        response = self.llm.complete(prompt, system="Valid JSON. hindi_text Devanagari only.", json_mode=True)
        return self.llm.parse_json(response.text)

    def generate(
        self,
        story: dict[str, Any],
        category_id: str,
        scene_image: Path,
        output_dir: Path,
        *,
        count: int = 3,
        all_scene_images: list[Path] | None = None,
    ) -> tuple[list[Path], list[dict], Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        concepts: list[dict] = []
        variants: list[Path] = []

        category = get_category(category_id)
        hero = pick_hero_scene(all_scene_images or [scene_image])
        hero_base = output_dir / "thumb_hero_base.jpg"
        enhance_scene_for_thumb(hero, hero_base)

        for i in range(count):
            concept = self._concept_prompt(story, category_id, i)
            concepts.append(concept)
            hi_text = (concept.get("hindi_text") or story.get("title", "")).strip()
            if len(hi_text) < 4:
                hi_text = (story.get("title") or "कहानी")[:32]
            art_path = output_dir / f"thumb_art_{i + 1}.png"

            art_prompt = (
                (concept.get("art_prompt_en") or category.thumbnail_tone)
                + ". NO TEXT, NO LETTERS, NO WATERMARK, ultra sharp, high contrast, "
                "single focal subject, rule of thirds"
            )
            used_ai = False
            try:
                if self.images.is_available() and i < 2:
                    self.images.generate(art_prompt, art_path, YOUTUBE_THUMB_SIZE, seed=2200 + i)
                    used_ai = art_path.exists() and art_path.stat().st_size > 40_000
            except Exception as exc:
                logger.warning("Thumbnail art %s failed: %s", i, exc)
            if not used_ai:
                shutil.copy(hero_base, art_path)

            if i == 1:
                with Image.open(art_path) as im:
                    base = ImageEnhance.Contrast(im.convert("RGB")).enhance(1.15)
                    base.save(art_path, quality=92)

            final_with_text = self.overlay.generate_variants(
                art_path, hi_text, output_dir, count=1
            )[0]
            dest = output_dir / f"thumb_v{i + 1}.jpg"
            if final_with_text.resolve() != dest.resolve():
                shutil.copy(final_with_text, dest)
            variants.append(dest)

        best = self.overlay.pick_best(variants)
        scores = self._score_variants(variants, concepts, category_id)
        for c, s in zip(concepts, scores):
            c["quality_score"] = s
        best_idx = scores.index(max(scores)) if scores else 0
        best = variants[best_idx]
        return variants, concepts, best

    def _score_variants(self, paths: list[Path], concepts: list[dict], category_id: str) -> list[float]:
        scores: list[float] = []
        for p, c in zip(paths, concepts):
            score = 0.5
            if p.exists() and p.stat().st_size > 80_000:
                score += 0.2
            text = c.get("hindi_text", "")
            if text and any("\u0900" <= ch <= "\u097f" for ch in text):
                score += 0.15
            if c.get("art_prompt_en"):
                score += 0.15
            scores.append(min(score, 1.0))
        return scores
