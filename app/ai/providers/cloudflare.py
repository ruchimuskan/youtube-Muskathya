from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.ai.providers.base import LLMProvider, LLMResponse
from app.config import get_settings

logger = logging.getLogger(__name__)

FALLBACK_MODELS = [
    "@cf/meta/llama-3.1-8b-instruct",
    "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
    "@cf/meta/llama-3-8b-instruct",
    "@cf/qwen/qwen2.5-7b-instruct",
    "@cf/mistral/mistral-7b-instruct-v0.2",
]


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

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=5, max=60),
        reraise=True,
    )
    def complete(self, prompt: str, *, system: str | None = None, json_mode: bool = False) -> LLMResponse:
        if not self.is_available():
            raise RuntimeError("Cloudflare Workers AI is not configured")

        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        headers = {"Authorization": f"Bearer {self.settings.cloudflare_api_token}"}
        payload: dict[str, Any] = {
            "messages": messages,
            "max_tokens": 4096,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        candidate_models = [self.settings.cloudflare_model]
        for fallback in FALLBACK_MODELS:
            if fallback not in candidate_models:
                candidate_models.append(fallback)

        last_error: Exception | None = None
        for model in candidate_models:
            url = (
                f"https://api.cloudflare.com/client/v4/accounts/"
                f"{self.settings.cloudflare_account_id}/ai/run/{model}"
            )
            try:
                with httpx.Client(timeout=120.0) as client:
                    resp = client.post(url, headers=headers, json=payload)
                    if resp.status_code == 429:
                        logger.warning(
                            "Cloudflare model %s returned 429 Too Many Requests. Trying fallback model...",
                            model,
                        )
                        last_error = RuntimeError(f"Rate limited (429) on {model}")
                        continue
                    if resp.status_code >= 500:
                        logger.warning(
                            "Cloudflare model %s returned %s server error. Trying fallback model...",
                            model,
                            resp.status_code,
                        )
                        last_error = RuntimeError(f"Server error {resp.status_code} on {model}")
                        continue
                    resp.raise_for_status()
                    data = resp.json()

                result = data.get("result", data)
                if isinstance(result, dict) and result.get("success") is False:
                    logger.warning("Cloudflare model %s returned unsuccessful payload: %s", model, result)
                    last_error = RuntimeError(f"Unsuccessful result on {model}: {result}")
                    continue

                text = _extract_text_from_result(result)
                if not text:
                    logger.warning("Cloudflare model %s returned empty text", model)
                    last_error = ValueError(f"Empty response from {model}")
                    continue

                return LLMResponse(
                    text=text,
                    provider=self.name,
                    model=model,
                    raw=data if isinstance(data, dict) else None,
                )
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 429:
                    logger.warning(
                        "Cloudflare model %s hit 429 rate limit. Trying fallback...",
                        model,
                    )
                    last_error = exc
                    continue
                last_error = exc
            except (httpx.RequestError, RuntimeError, ValueError) as exc:
                logger.warning("Error with Cloudflare model %s: %s", model, exc)
                last_error = exc

        raise RuntimeError(f"All Cloudflare models failed. Last error: {last_error}")
