from __future__ import annotations

import logging

from app.ai.json_utils import parse_json_object
from app.ai.providers.base import LLMProvider, LLMResponse
from app.ai.providers.cloudflare import CloudflareWorkersAI
from app.ai.providers.gemini import GeminiProvider
from app.ai.providers.ollama import OllamaProvider
from app.config import get_settings
from app.database import Repository, session_scope

logger = logging.getLogger(__name__)


class LLMRouter:
    """Selects Cloudflare, Gemini, or Ollama based on settings, quota, and availability."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._cloudflare = CloudflareWorkersAI()
        self._gemini = GeminiProvider()
        self._ollama = OllamaProvider()

    def _pick_provider(self) -> LLMProvider:
        mode = self.settings.ai_provider
        if mode == "gemini":
            if not self._gemini.is_available():
                raise RuntimeError("Gemini API is not configured (set GEMINI_API_KEY)")
            return self._gemini
        if mode == "ollama":
            if not self._ollama.is_available():
                raise RuntimeError("Ollama is not available")
            return self._ollama
        if mode == "cloudflare":
            if self._cloudflare.is_available():
                return self._cloudflare
            if self._gemini.is_available():
                logger.info("Cloudflare not configured, using Gemini")
                return self._gemini
            raise RuntimeError("Cloudflare Workers AI is not configured")

        # auto
        if self._cloudflare.is_available():
            with session_scope() as session:
                repo = Repository(session)
                used = repo.cloudflare_usage_today()
            if used < self.settings.ai_cloudflare_daily_limit:
                return self._cloudflare
            logger.warning("Cloudflare daily limit reached (%s)", used)

        if self._gemini.is_available():
            return self._gemini
        if self._ollama.is_available():
            return self._ollama
        if self._cloudflare.is_available():
            return self._cloudflare
        raise RuntimeError("No LLM provider available (configure Cloudflare, Gemini, or start Ollama)")

    def complete(
        self, prompt: str, *, system: str | None = None, json_mode: bool = False
    ) -> LLMResponse:
        provider = self._pick_provider()
        try:
            response = provider.complete(prompt, system=system, json_mode=json_mode)
            with session_scope() as session:
                repo = Repository(session)
                repo.log_ai_usage(
                    provider=response.provider,
                    model=response.model,
                    tokens=max(len(prompt) // 4, 1),
                    success=True,
                )
            return response
        except Exception as exc:
            logger.warning("Provider %s failed: %s", provider.name, exc)
            with session_scope() as session:
                repo = Repository(session)
                repo.log_ai_usage(
                    provider=str(provider.name),
                    model=str(
                        getattr(provider, "settings", self.settings).cloudflare_model
                        if provider.name == "cloudflare"
                        else getattr(provider, "model", "default")
                    ),
                    tokens=0,
                    success=False,
                )
            # Fallback to Gemini if Cloudflare fails
            if provider.name != "gemini" and self._gemini.is_available():
                logger.info("Retrying with Gemini after %s failure", provider.name)
                try:
                    response = self._gemini.complete(prompt, system=system, json_mode=json_mode)
                    with session_scope() as session:
                        Repository(session).log_ai_usage(
                            provider=response.provider,
                            model=response.model,
                            tokens=max(len(prompt) // 4, 1),
                            success=True,
                        )
                    return response
                except Exception as g_exc:
                    logger.warning("Gemini fallback also failed: %s", g_exc)

            # Fallback to Ollama
            if provider.name != "ollama" and self._ollama.is_available():
                logger.info("Retrying with Ollama after %s failure", provider.name)
                response = self._ollama.complete(prompt, system=system, json_mode=json_mode)
                with session_scope() as session:
                    Repository(session).log_ai_usage(
                        provider=response.provider,
                        model=response.model,
                        tokens=max(len(prompt) // 4, 1),
                        success=True,
                    )
                return response
            raise

    @staticmethod
    def parse_json(text: str) -> dict:
        return parse_json_object(text)
