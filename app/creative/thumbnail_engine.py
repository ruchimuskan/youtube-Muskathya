from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Any

from PIL import Image, ImageEnhance

from app.ai.providers import LLMRouter
from app.config import get_settings
from app.content.categories import get_category
from app.creative.hindi_thumbnail_copy import resolve_overlay_text, sanitize_hindi
from app.creative.story_thumbnail_analyzer import StoryThumbnailAnalyzer
from app.creative.thumbnail_art_fallback import create_story_fallback_art
from app.creative.thumbnail_character_bible import (
    THUMB_NEGATIVE_EXTRA,
    apply_character_bible,
    build_composition_block,
    story_has_shiva_ganesha,
)
from app.creative.thumbnail_paths import canonical_thumbnail_path, story_thumbnail_in_workdir
from app.creative.thumbnail_qc import validate_thumbnail
from app.images.cloudflare_image import CloudflareImageGenerator
from app.video.thumbnail_generator import ThumbnailGenerator, YOUTUBE_THUMB_SIZE

logger = logging.getLogger(__name__)

CINEMATIC_PREFIX = (
    "Premium Indian YouTube thumbnail key art, ultra HD 3D cinematic CGI animation, "
    "Pixar-quality mythological style, NOT a photograph, NOT stock image, NO TEXT, NO LETTERS"
)


class ThumbnailEngine:
    """Story JSON → analysis → SDXL poster (no text) → validated Hindi overlay → QC."""

    def __init__(self, llm: LLMRouter | None = None) -> None:
        self.llm = llm or LLMRouter()
        self.analyzer = StoryThumbnailAnalyzer(self.llm)
        self.overlay = ThumbnailGenerator()
        self.images = CloudflareImageGenerator()
        self.settings = get_settings()

    def _scene_narration(self, story: dict, scene_number: int) -> str:
        for s in story.get("scenes") or []:
            if int(s.get("scene_number", 0)) == int(scene_number):
                return (s.get("narration") or "")[:300]
        return ""

    def _build_image_prompt(self, story: dict, category_id: str, analysis: dict) -> str:
        category = get_category(category_id)

        if story_has_shiva_ganesha(story):
            # Compact prompt — Cloudflare SDXL rejects very long / duplicate deity blocks
            return (
                f"{CINEMATIC_PREFIX}. Wide medium-close YouTube thumbnail, TWO characters visible in same frame (65% of image). "
                "LEFT character: blue-skinned Hindu god Shiva, long matted jata hair, crescent moon, third eye, "
                "rudraksha beads, offering a glowing golden divine candle with both hands. "
                "RIGHT character: young god Ganesha, elephant head with long trunk and big ears, tusks, golden crown, "
                "NOT a human woman, NOT a human boy face, NOT goddess Parvati, only elephant-headed Ganesha. "
                "Both look at the candle between them. Mount Kailash Himalaya background, golden divine rays. "
                "3D CGI Pixar-style Indian mythology, sharp, vibrant, absolutely NO TEXT NO LETTERS NO CAPTIONS "
                "NO SUBTITLES NO WATERMARK, no modern clothing."
            )

        chars = analysis.get("main_characters") or []
        char_block = " | ".join(
            f"{c.get('name')}: {(c.get('appearance_en', '') or '')[:120]}. "
            f"Expression: {c.get('expression')}. Pose: {c.get('pose_action')}"
            for c in chars[:3]
            if isinstance(c, dict)
        )
        scene_n = int(analysis.get("best_scene_number") or 5)
        narration = self._scene_narration(story, scene_n)[:180]

        return (
            f"{CINEMATIC_PREFIX}. {build_composition_block(analysis, category_id)[:300]} "
            f"Moment: {(analysis.get('focal_moment_en') or '')[:160]}. "
            f"Context: {narration}. "
            f"Characters: {char_block[:400]}. "
            f"Key object: {(analysis.get('key_object') or '')[:80]}. "
            f"Background: {(analysis.get('background_en') or category.visual_style)[:120]}. "
            f"{category.thumbnail_tone}."
        )[:1800]

    def _generate_art(self, prompt: str, out: Path, seed: int) -> bool:
        if not self.images.is_available():
            return False
        for attempt in range(max(1, self.settings.image_max_retries)):
            try:
                self.images.generate(
                    prompt,
                    out,
                    YOUTUBE_THUMB_SIZE,
                    seed=seed + attempt * 31,
                    negative_prompt=THUMB_NEGATIVE_EXTRA,
                )
                if out.exists() and out.stat().st_size > 55_000:
                    return True
            except Exception as exc:
                logger.warning("Thumbnail SDXL attempt %s: %s", attempt + 1, exc)
        return False

    def generate(
        self,
        story: dict[str, Any],
        category_id: str,
        scene_image: Path | None,
        output_dir: Path,
        *,
        count: int = 3,
        all_scene_images: list[Path] | None = None,
    ) -> tuple[list[Path], list[dict], Path]:
        _ = scene_image, all_scene_images
        output_dir.mkdir(parents=True, exist_ok=True)
        story_id = story.get("story_project_id")

        analysis = self.analyzer.analyze(story, category_id)
        analysis = apply_character_bible(story, category_id, analysis)

        headline, suspense, locked = resolve_overlay_text(story, category_id, analysis)
        analysis["hindi_headline"] = headline
        analysis["hindi_suspense"] = suspense
        analysis["hindi_copy_locked"] = locked

        (output_dir / "thumbnail_analysis.json").write_text(
            json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        scheme = "gold"
        concepts: list[dict] = []
        variants: list[Path] = []
        variant_count = max(1, min(count, 5))
        base_prompt = self._build_image_prompt(story, category_id, analysis)

        for i in range(variant_count):
            concept = {**analysis, "variant": i + 1}
            art_path = output_dir / f"thumb_art_{i + 1}.png"
            seed = 8800 + int(story_id or 0) * 13 + i * 97
            prompt = base_prompt
            if i == 1:
                prompt += " Tighter framing on deity faces and glowing candle."
            elif i == 2:
                prompt += " Slightly stronger divine golden rim light on characters."

            used_ai = self._generate_art(prompt, art_path, seed=seed)
            concept["art_source"] = "sdxl_cinematic" if used_ai else "category_fallback"

            if not used_ai:
                create_story_fallback_art(category_id, art_path)

            with Image.open(art_path) as im:
                im = ImageEnhance.Contrast(im.convert("RGB")).enhance(1.16)
                im = ImageEnhance.Color(im).enhance(1.12)
                im = ImageEnhance.Sharpness(im).enhance(1.25)
                im.save(art_path, quality=96)

            bg_only = output_dir / f"thumb_art_{i + 1}_no_text.png"
            shutil.copy(art_path, bg_only)

            final = output_dir / f"thumb_v{i + 1}.jpg"
            self.overlay.apply_story_overlay(
                art_path,
                headline,
                final,
                suspense=suspense,
                text_scheme=scheme,
            )
            analysis["approved_headline"] = headline
            analysis["approved_suspense"] = suspense
            qc = validate_thumbnail(
                final,
                analysis=analysis,
                expected_headline=headline,
            )
            concept["qc_passed"] = qc.passed
            concept["qc_issues"] = qc.issues
            variants.append(final)
            concepts.append(concept)

        best = self.overlay.pick_best(variants) if len(variants) > 1 else variants[0]
        canonical = story_thumbnail_in_workdir(output_dir.parent, story_id)
        shutil.copy(best, canonical)
        shutil.copy(best, canonical_thumbnail_path(story_id))
        logger.info("Saved canonical thumbnail %s", canonical_thumbnail_path(story_id))

        for c in concepts:
            c["hindi_text"] = sanitize_hindi(headline)
            c["hindi_suspense"] = sanitize_hindi(suspense)

        return variants, concepts, best
