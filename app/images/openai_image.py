from __future__ import annotations

import base64
import logging
from io import BytesIO
from pathlib import Path
from typing import Any

import httpx
from PIL import Image

from app.config import get_settings
from app.images.image_validator import is_valid_scene_image

logger = logging.getLogger(__name__)


class OpenAIImageGenerator:
    """
    Native OpenAI Images API generator (DALL-E 3).
    Produces 1792x1024 photorealistic widescreen Bollywood movie poster key art.
    """

    def __init__(self) -> None:
        self.settings = get_settings()

    def is_available(self) -> bool:
        return bool(getattr(self.settings, "openai_api_key", None))

    def generate(
        self,
        prompt: str,
        out: Path,
        size: tuple[int, int] = (1280, 720),
        *,
        model: str | None = None,
        quality: str = "standard",
        style: str = "vivid",
    ) -> Path:
        if not self.is_available():
            raise RuntimeError("OpenAI API key not configured")

        target_w, target_h = size
        chosen_model = model or getattr(self.settings, "openai_image_model", "dall-e-3")
        headers = {
            "Authorization": f"Bearer {self.settings.openai_api_key}",
            "Content-Type": "application/json",
        }

        # DALL-E 3 accepts 1792x1024, 1024x1024, or 1024x1792
        if "dall-e-3" in chosen_model.lower():
            native_size = "1792x1024" if target_w >= target_h else "1024x1792"
        else:
            native_size = "1024x1024"

        payload: dict[str, Any] = {
            "model": chosen_model,
            "prompt": prompt[:4000],
            "size": native_size,
            "n": 1,
            "response_format": "b64_json",
        }
        if "dall-e-3" in chosen_model.lower():
            payload["quality"] = quality
            payload["style"] = style

        url = "https://api.openai.com/v1/images/generations"
        logger.info("Requesting OpenAI image generation (%s, %s)...", chosen_model, native_size)

        with httpx.Client(timeout=httpx.Timeout(90.0, connect=20.0)) as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code == 429:
                raise RuntimeError("OpenAI image quota exceeded (429)")
            if resp.status_code == 401:
                raise RuntimeError("OpenAI API authentication failed (401)")
            resp.raise_for_status()
            data = resp.json()

        items = data.get("data") or []
        if not items:
            raise RuntimeError(f"OpenAI returned empty data: {data}")

        first_item = items[0]
        raw_bytes: bytes | None = None

        if "b64_json" in first_item:
            raw_bytes = base64.b64decode(first_item["b64_json"])
        elif "url" in first_item:
            img_url = first_item["url"]
            with httpx.Client(timeout=30.0) as dl_client:
                dl_resp = dl_client.get(img_url)
                dl_resp.raise_for_status()
                raw_bytes = dl_resp.content

        if not raw_bytes:
            raise RuntimeError("Failed to decode image bytes from OpenAI response")

        out.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(BytesIO(raw_bytes)) as im:
            im = im.convert("RGB").resize((target_w, target_h), Image.Resampling.LANCZOS)
            im.save(out, format="PNG", optimize=True)

        if not is_valid_scene_image(out):
            raise RuntimeError(f"OpenAI generated image failed quality check: {out}")

        logger.info("Successfully generated OpenAI image: %s (%dx%d)", out, target_w, target_h)
        return out
