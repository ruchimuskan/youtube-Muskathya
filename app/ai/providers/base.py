from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class LLMResponse:
    text: str
    provider: str
    model: str
    raw: dict[str, Any] | None = None


class LLMProvider(ABC):
    name: str

    @abstractmethod
    def complete(self, prompt: str, *, system: str | None = None, json_mode: bool = False) -> LLMResponse:
        raise NotImplementedError

    @abstractmethod
    def is_available(self) -> bool:
        raise NotImplementedError
