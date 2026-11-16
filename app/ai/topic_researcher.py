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
        prompt = f"""You are an elite Indian thriller novelist, Bollywood screenplay strategist, and high-retention YouTube content creator.
Language: {language}
Genre: {genre}
Format: {"YouTube Short (under 60s narration)" if is_short else "Long-form (6-12 min narration)"}

STRICT PROHIBITION - REJECT GENERIC CONCEPTS:
- NO repeated poor girl/rich boy love stories.
- NO generic mother-son sacrifice melodrama.
- NO predictable village moral lectures.
- NO repetitive ghost/daayan stories.
- NO stories where everything is obvious from the start.

CONCEPT SELECTION PROCESS:
Secretly evaluate 10 distinct story premises. Grade each on:
1. Originality (fresh Indian setting and unique dilemma)
2. Curiosity & Cold Hook (first 10 seconds shock factor)
3. Suspense (escalating tension every 30-45s)
4. Emotional impact (relatable characters with believable stakes)
5. Twist potential (foreshadowed, mind-bending resolution)
6. Thumbnail potential (high click-through-rate visual intrigue)
Select ONLY the single most unusual, compelling, and addictive concept.

Past lessons from this channel (apply them):
{chr(10).join(lessons) if lessons else "None yet."}

Topics to avoid (already used recently):
{", ".join(avoid) if avoid else "None specified."}

Respond with JSON only:
{{
  "main_topic": "Gripping Hindi title/concept",
  "audience_hook": "Shocking 0-10 second opening incident or dialogue",
  "conflict_and_stakes": "Central dilemma and what the characters stand to lose",
  "planned_twist": "Unexpected but logical plot reversal with planted clues",
  "search_intent": "Why viewers are drawn to this theme",
  "content_gap": "What makes this different from generic YouTube stories",
  "suggested_keywords": ["...", "..."],
  "thumbnail_idea": "Intense visual moment for thumbnail",
  "uniqueness_note": "Why this is original and addictive"
}}"""

        response = self.llm.complete(
            prompt,
            system="You are an elite Indian story creator and YouTube retention specialist. Output valid JSON only. 100% original, unpredictable concepts only.",
            json_mode=True,
        )
        return self.llm.parse_json(response.text)
