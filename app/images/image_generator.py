from __future__ import annotations

import logging
import random
import shutil
from pathlib import Path

import httpx
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from app.config import get_settings
from app.images.character_manager import CharacterManager
from app.images.cloudflare_image import CloudflareImageGenerator
from app.images.image_validator import is_valid_scene_image
from app.images.prompt_builder import build_sdxl_prompt

logger = logging.getLogger(__name__)


class ImageGenerator:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.cf_images = CloudflareImageGenerator()

    def _comfy_available(self) -> bool:
        if not self.settings.comfyui_enabled:
            return False
        try:
            with httpx.Client(timeout=3.0) as client:
                r = client.get(f"{self.settings.comfyui_url}/system_stats")
                return r.status_code == 200
        except httpx.HTTPError:
            return False

    def _cinematic_placeholder(self, path: Path, prompt: str, size: tuple[int, int]) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        w, h = size
        seed = abs(hash(prompt)) % 360
        base = Image.new("RGB", size, (20 + seed % 40, 28, 48))
        draw = ImageDraw.Draw(base)
        for i in range(0, w, 80):
            shade = 30 + (i // 80) % 50
            draw.rectangle([(i, 0), (i + 40, h)], fill=(shade, shade + 10, shade + 30))
        base = base.filter(ImageFilter.GaussianBlur(radius=2))
        overlay = ImageEnhance.Brightness(base).enhance(1.1)
        draw = ImageDraw.Draw(overlay)
        caption = (prompt[:100] + "…") if len(prompt) > 100 else prompt
        try:
            font = ImageFont.load_default()
        except OSError:
            font = None
        draw.text((40, h - 120), caption, fill=(230, 230, 240), font=font)
        overlay.save(path, quality=92)
        return path

    def _fallback_asset(self, path: Path, size: tuple[int, int], prompt: str) -> Path:
        fallbacks = list(self.settings.image_fallback_dir.glob("*.jpg"))
        fallbacks += list(self.settings.image_fallback_dir.glob("*.png"))
        if fallbacks:
            src = random.choice(fallbacks)
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(src, path)
            with Image.open(path) as im:
                im.convert("RGB").resize(size, Image.Resampling.LANCZOS).save(path)
            return path
        return self._cinematic_placeholder(path, prompt, size)

    def _generate_cloudflare_with_retries(
        self,
        prompt: str,
        out: Path,
        size: tuple[int, int],
        char_mgr: CharacterManager,
        scene: dict,
    ) -> None:
        base_seed = char_mgr.character_seed(f"scene_{scene.get('scene_number')}")
        last_err: Exception | None = None
        for attempt in range(self.settings.image_max_retries):
            seed = base_seed + attempt * 17
            try:
                self.cf_images.generate(prompt, out, size, seed=seed)
                if is_valid_scene_image(out):
                    return
            except Exception as exc:
                last_err = exc
                logger.warning(
                    "Cloudflare image attempt %s scene %s: %s",
                    attempt + 1,
                    scene.get("scene_number"),
                    exc,
                )
        raise RuntimeError(
            f"Cloudflare image failed after {self.settings.image_max_retries} tries: {last_err}"
        )

    def generate_scene_images(
        self,
        story: dict,
        output_dir: Path,
        aspect_ratio: str = "16:9",
    ) -> tuple[list[Path], list[dict]]:
        size = (1080, 1920) if aspect_ratio == "9:16" else (1920, 1080)
        char_mgr = CharacterManager(story)
        paths: list[Path] = []
        prompts_log: list[dict] = []
        for scene in story.get("scenes", []):
            sn = scene.get("scene_number", len(paths) + 1)
            prompt = build_sdxl_prompt(story, scene)
            log_prompt = char_mgr.scene_prompt(scene)
            out = output_dir / f"scene_{sn:03d}.png"
            prompts_log.append({"scene_number": sn, "prompt": log_prompt, "sdxl_prompt": prompt})

            generated = False
            if self._comfy_available():
                try:
                    self._generate_comfy(log_prompt, out, size, char_mgr, scene)
                    generated = is_valid_scene_image(out)
                except Exception as exc:
                    logger.warning("ComfyUI failed scene %s: %s", sn, exc)

            if not generated and self.cf_images.is_available():
                try:
                    self._generate_cloudflare_with_retries(prompt, out, size, char_mgr, scene)
                    generated = True
                except Exception as exc:
                    logger.error("Cloudflare image failed scene %s: %s", sn, exc)

            if not generated:
                if self.settings.allow_placeholder_images:
                    self._fallback_asset(out, size, prompt)
                else:
                    raise RuntimeError(
                        f"Scene {sn}: real AI image required but generation failed"
                    )

            if not is_valid_scene_image(out):
                if self.settings.allow_placeholder_images:
                    self._fallback_asset(out, size, prompt)
                else:
                    raise RuntimeError(f"Scene {sn}: generated image failed validation")

            paths.append(out)

        return paths, prompts_log

    def _generate_comfy(
        self,
        prompt: str,
        out: Path,
        size: tuple[int, int],
        char_mgr: CharacterManager,
        scene: dict,
    ) -> None:
        width, height = size
        seed = char_mgr.character_seed(f"scene_{scene.get('scene_number')}")

        workflow = {
            "prompt": {
                "3": {
                    "class_type": "KSampler",
                    "inputs": {
                        "seed": seed,
                        "steps": 20,
                        "cfg": 7,
                        "sampler_name": "euler",
                        "scheduler": "normal",
                        "denoise": 1,
                        "model": ["4", 0],
                        "positive": ["6", 0],
                        "negative": ["7", 0],
                        "latent_image": ["5", 0],
                    },
                },
                "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "model.safetensors"}},
                "5": {
                    "class_type": "EmptyLatentImage",
                    "inputs": {"width": width, "height": height, "batch_size": 1},
                },
                "6": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["4", 1]}},
                "7": {
                    "class_type": "CLIPTextEncode",
                    "inputs": {"text": self.settings.image_negative_prompt, "clip": ["4", 1]},
                },
                "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
                "9": {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": "ytcm"}},
            }
        }

        with httpx.Client(timeout=300.0) as client:
            resp = client.post(f"{self.settings.comfyui_url}/prompt", json=workflow)
            resp.raise_for_status()
            prompt_id = resp.json().get("prompt_id")
            if not prompt_id:
                raise RuntimeError("ComfyUI did not return prompt_id")

            import time

            for _ in range(120):
                time.sleep(2)
                hist = client.get(f"{self.settings.comfyui_url}/history/{prompt_id}")
                if hist.status_code != 200:
                    continue
                data = hist.json()
                if prompt_id in data:
                    outputs = data[prompt_id].get("outputs", {})
                    for node_out in outputs.values():
                        for img in node_out.get("images", []):
                            img_resp = client.get(
                                f"{self.settings.comfyui_url}/view",
                                params={
                                    "filename": img["filename"],
                                    "subfolder": img.get("subfolder", ""),
                                    "type": img.get("type", "output"),
                                },
                            )
                            img_resp.raise_for_status()
                            out.parent.mkdir(parents=True, exist_ok=True)
                            out.write_bytes(img_resp.content)
                            return
            raise TimeoutError("ComfyUI image generation timed out")
