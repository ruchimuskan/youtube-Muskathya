from __future__ import annotations

import logging
from typing import Any

from app.ai.providers import LLMRouter
from app.database import Repository, session_scope

logger = logging.getLogger(__name__)

GENRES = [
    "emotional",
    "moral",
    "mystery",
    "suspense",
    "horror",
    "motivational",
    "family",
    "children",
]


class TopicResearcher:
    """Suggests original topics using prior performance lessons (no external paid APIs)."""

    def __init__(self, llm: LLMRouter | None = None) -> None:
        self.llm = llm or LLMRouter()

    def suggest_topic(
        self,
        language: str,
        genre: str,
        is_short: bool,
        avoid_topics: list[str] | None = None,
    ) -> dict[str, Any]:
        lessons: list[str] = []
        with session_scope() as session:
            for row in Repository(session).get_recent_lessons(15):
                lessons.append(f"[{row.category}] {row.lesson}")

        avoid = avoid_topics or []
        prompt = f"""You are a YouTube content strategist for original story channels.
Language: {language}
Genre: {genre}
Format: {"YouTube Short (under 60s narration)" if is_short else "Long-form (5-12 min narration)"}

Past lessons from this channel (apply them):
{chr(10).join(lessons) if lessons else "None yet."}

Topics to avoid (already used recently):
{", ".join(avoid) if avoid else "None specified."}

Respond with JSON only:
{{
  "main_topic": "...",
  "audience_hook": "...",
  "search_intent": "...",
  "content_gap": "...",
  "suggested_keywords": ["...", "..."],
  "uniqueness_note": "why this is original"
}}"""

        response = self.llm.complete(
            prompt,
            system="Output valid JSON only. Create 100% original ideas; never copy existing creators.",
            json_mode=True,
        )
        return self.llm.parse_json(response.text)
