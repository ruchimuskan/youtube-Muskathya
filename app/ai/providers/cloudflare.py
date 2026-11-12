from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.ai.providers.base import LLMProvider, LLMResponse
from app.config import get_settings

logger = logging.getLogger(__name__)


def _coerce_llm_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _extract_text_from_result(result: Any) -> str:
    if isinstance(result, str):
        return result.strip()
    if not isinstance(result, dict):
        return _coerce_llm_text(result).strip()

    for key in ("response", "text", "output", "content"):
        if key in result:
            text = _coerce_llm_text(result[key]).strip()
            if text:
                return text

    choices = result.get("choices")
    if isinstance(choices, list) and choices:
        msg = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
        text = _coerce_llm_text(msg.get("content")).strip()
        if text:
            return text

    return ""


class CloudflareWorkersAI(LLMProvider):
    name = "cloudflare"

    def __init__(self) -> None:
        self.settings = get_settings()

    def is_available(self) -> bool:
        return bool(self.settings.cloudflare_account_id and self.settings.cloudflare_api_token)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30))
    def complete(self, prompt: str, *, system: str | None = None, json_mode: bool = False) -> LLMResponse:
        if not self.is_available():
            raise RuntimeError("Cloudflare Workers AI is not configured")

        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        url = (
            f"https://api.cloudflare.com/client/v4/accounts/"
            f"{self.settings.cloudflare_account_id}/ai/run/{self.settings.cloudflare_model}"
        )
        headers = {"Authorization": f"Bearer {self.settings.cloudflare_api_token}"}
        payload: dict[str, Any] = {
            "messages": messages,
            "max_tokens": 6144,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        with httpx.Client(timeout=120.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code == 429:
                raise RuntimeError("Cloudflare rate limit exceeded")
            resp.raise_for_status()
            data = resp.json()

        result = data.get("result", data)
        if isinstance(result, dict) and result.get("success") is False:
            raise RuntimeError(f"Cloudflare AI error: {result}")

        text = _extract_text_from_result(result)
        if not text:
            raise ValueError(f"Empty response from Cloudflare Workers AI: {data!r}")

        return LLMResponse(
            text=text,
            provider=self.name,
            model=self.settings.cloudflare_model,
            raw=data if isinstance(data, dict) else None,
        )
