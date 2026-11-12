from __future__ import annotations

import logging
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.ai.providers.base import LLMProvider, LLMResponse
from app.config import get_settings

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self) -> None:
        self.settings = get_settings()

    def is_available(self) -> bool:
        try:
            with httpx.Client(timeout=5.0) as client:
                r = client.get(f"{self.settings.ollama_base_url}/api/tags")
                return r.status_code == 200
        except httpx.HTTPError:
            return False

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=10))
    def complete(self, prompt: str, *, system: str | None = None, json_mode: bool = False) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": self.settings.ollama_model,
            "prompt": prompt,
            "stream": False,
        }
        if system:
            payload["system"] = system
        if json_mode:
            payload["format"] = "json"

        with httpx.Client(timeout=300.0) as client:
            resp = client.post(f"{self.settings.ollama_base_url}/api/generate", json=payload)
            resp.raise_for_status()
            data = resp.json()

        text = data.get("response", "").strip()
        if not text:
            raise ValueError("Empty response from Ollama")

        return LLMResponse(
            text=text,
            provider=self.name,
            model=self.settings.ollama_model,
            raw=data,
        )
