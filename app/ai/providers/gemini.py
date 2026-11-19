from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from app.ai.providers.base import LLMProvider, LLMResponse
from app.config import get_settings

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, api_key: str | None = None, model: str = "gemini-2.0-flash") -> None:
        self.settings = get_settings()
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or getattr(self.settings, "gemini_api_key", "")
        self.model = model

    def is_available(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 5)

    def complete(self, prompt: str, *, system: str | None = None, json_mode: bool = False) -> LLMResponse:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
            f"?key={self.api_key}"
        )
        contents: list[dict[str, Any]] = []
        if system:
            contents.append({"role": "user", "parts": [{"text": f"System instructions:\n{system}"}]})
            contents.append({"role": "model", "parts": [{"text": "Understood. I will strictly follow these instructions."}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        gen_config: dict[str, Any] = {
            "temperature": 0.7,
            "maxOutputTokens": 4096,
        }
        if json_mode:
            gen_config["responseMimeType"] = "application/json"

        body = {
            "contents": contents,
            "generationConfig": gen_config,
        }

        with httpx.Client(timeout=120.0) as client:
            resp = client.post(url, json=body)
            resp.raise_for_status()
            data = resp.json()

        candidates = data.get("candidates", [])
        if not candidates:
            raise ValueError(f"Empty Gemini response: {data}")
        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts if "text" in p).strip()
        if not text:
            raise ValueError(f"No text parts in Gemini response: {data}")

        return LLMResponse(
            text=text,
            provider=self.name,
            model=self.model,
            raw=data,
        )
