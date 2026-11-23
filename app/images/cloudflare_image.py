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

DEFAULT_CLOUDFLARE_IMAGE_MODELS: list[str] = [
    "@cf/bytedance/stable-diffusion-xl-lightning",
    "@cf/black-forest-labs/flux-1-schnell",
]


class CloudflareImageGenerator:
    def __init__(self) -> None:
        self.settings = get_settings()

    def is_available(self) -> bool:
        return bool(
            self.settings.cloudflare_image_enabled
            and self.settings.cloudflare_account_id
            and self.settings.cloudflare_api_token
        )

    def _candidate_models(self) -> list[str]:
        models = [self.settings.cloudflare_image_model]
        for m in DEFAULT_CLOUDFLARE_IMAGE_MODELS:
            if m not in models:
                models.append(m)
        return models

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

        headers = {"Authorization": f"Bearer {self.settings.cloudflare_api_token}"}
        neg = self.settings.image_negative_prompt
        if negative_prompt:
            neg = f"{neg}, {negative_prompt}"

        last_exc: Exception | None = None
        models = self._candidate_models()

        for model in models:
            url = (
                f"https://api.cloudflare.com/client/v4/accounts/"
                f"{self.settings.cloudflare_account_id}/ai/run/{model}"
            )
            payload: dict[str, Any] = {
                "prompt": prompt,
                "width": gen_w,
                "height": gen_h,
            }
            if "flux" in model.lower():
                payload["num_steps"] = 4
            else:
                payload["negative_prompt"] = neg
                payload["num_steps"] = (
                    min(max(self.settings.image_num_steps, 4), 8)
                    if "lightning" in model.lower()
                    else self.settings.image_num_steps
                )
                payload["guidance"] = guidance if guidance is not None else self.settings.image_guidance

            if seed is not None:
                payload["seed"] = seed

            try:
                # Fast timeout (60s) so stuck cloud workers fail fast and retry quickly
                with httpx.Client(timeout=httpx.Timeout(60.0, connect=15.0)) as client:
                    resp = client.post(url, headers=headers, json=payload)
                    if resp.status_code in (404, 410):
                        logger.warning(
                            "Cloudflare image model %s returned HTTP %s (deprecated/not found). Trying fallback model...",
                            model,
                            resp.status_code,
                        )
                        continue
                    if resp.status_code == 429:
                        logger.warning(
                            "Cloudflare image model %s returned 429 quota exceeded. Trying fallback model...",
                            model,
                        )
                        continue
                    if resp.status_code == 408:
                        raise RuntimeError(f"Cloudflare image request timed out (408) on {model}")
                    if resp.status_code in (502, 503, 504):
                        raise RuntimeError(f"Cloudflare server error ({resp.status_code}) on {model}")
                    resp.raise_for_status()
                    raw_bytes = self._read_image_bytes(resp)

                if not raw_bytes:
                    raise RuntimeError(f"Empty image response from Cloudflare ({model})")

                out.parent.mkdir(parents=True, exist_ok=True)
                with Image.open(BytesIO(raw_bytes)) as im:
                    im = im.convert("RGB").resize((target_w, target_h), Image.Resampling.LANCZOS)
                    im.save(out, format="PNG", optimize=True)

                if not is_valid_scene_image(out):
                    raise RuntimeError(f"Generated image failed quality check: {out}")

                return out
            except Exception as exc:
                last_exc = exc
                logger.warning("Cloudflare image attempt failed on %s: %s", model, exc)

        raise RuntimeError(f"All Cloudflare image models failed: {last_exc}")

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
