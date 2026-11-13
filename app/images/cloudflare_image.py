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


class CloudflareImageGenerator:
    def __init__(self) -> None:
        self.settings = get_settings()

    def is_available(self) -> bool:
        return bool(
            self.settings.cloudflare_image_enabled
            and self.settings.cloudflare_account_id
            and self.settings.cloudflare_api_token
        )

    def generate(
        self,
        prompt: str,
        out: Path,
        size: tuple[int, int],
        *,
        seed: int | None = None,
        negative_prompt: str | None = None,
        guidance: float | None = None,
    ) -> Path:
        if not self.is_available():
            raise RuntimeError("Cloudflare image generation not configured")

        target_w, target_h = size
        gen_w = self.settings.image_gen_width
        gen_h = self.settings.image_gen_height
        if target_h > target_w:
            gen_w, gen_h = min(gen_w, gen_h), max(gen_w, gen_h)

        url = (
            f"https://api.cloudflare.com/client/v4/accounts/"
            f"{self.settings.cloudflare_account_id}/ai/run/{self.settings.cloudflare_image_model}"
        )
        headers = {"Authorization": f"Bearer {self.settings.cloudflare_api_token}"}
        neg = self.settings.image_negative_prompt
        if negative_prompt:
            neg = f"{neg}, {negative_prompt}"
        payload: dict[str, Any] = {
            "prompt": prompt,
            "negative_prompt": neg,
            "width": gen_w,
            "height": gen_h,
            "num_steps": (
                max(self.settings.image_num_steps, 28)
                if guidance is not None
                else self.settings.image_num_steps
            ),
            "guidance": guidance if guidance is not None else self.settings.image_guidance,
        }
        if seed is not None:
            payload["seed"] = seed

        with httpx.Client(timeout=180.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code == 429:
                raise RuntimeError("Cloudflare image quota exceeded")
            resp.raise_for_status()
            raw_bytes = self._read_image_bytes(resp)

        if not raw_bytes:
            raise RuntimeError("Empty image response from Cloudflare")

        out.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(BytesIO(raw_bytes)) as im:
            im = im.convert("RGB").resize((target_w, target_h), Image.Resampling.LANCZOS)
            im.save(out, format="PNG", optimize=True)

        if not is_valid_scene_image(out):
            raise RuntimeError(f"Generated image failed quality check: {out}")

        return out

    def _read_image_bytes(self, resp: httpx.Response) -> bytes:
        ctype = (resp.headers.get("content-type") or "").lower()
        if ctype.startswith("image/") or resp.content[:4] == b"\x89PNG" or resp.content[:2] == b"\xff\xd8":
            return resp.content
        data = resp.json()
        if not data.get("success", True) and not data.get("result"):
            raise RuntimeError(f"Cloudflare image API error: {data}")
        result = data.get("result", data)
        extracted = self._extract_image_bytes(result, resp.content)
        if extracted:
            return extracted
        raise RuntimeError(f"Unrecognized Cloudflare image payload keys: {list(data.keys())}")

    def _extract_image_bytes(self, result: Any, fallback_body: bytes) -> bytes | None:
        if isinstance(result, dict):
            if "image" in result:
                val = result["image"]
                if isinstance(val, str):
                    return base64.b64decode(val)
                if isinstance(val, bytes):
                    return val
            for key in ("bytes", "data", "output"):
                val = result.get(key)
                if isinstance(val, str):
                    try:
                        return base64.b64decode(val)
                    except Exception:
                        pass
        if fallback_body[:4] == b"\x89PNG" or fallback_body[:2] == b"\xff\xd8":
            return fallback_body
        return None
