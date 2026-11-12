from __future__ import annotations

from typing import Any

from app.ai.providers import LLMRouter


class SEOGenerator:
    def __init__(self, llm: LLMRouter | None = None) -> None:
        self.llm = llm or LLMRouter()

    def generate(self, story: dict[str, Any], language: str) -> dict[str, Any]:
        research = story.get("research", {})
        hindi_rule = ""
        if language == "hi":
            hindi_rule = (
                "- recommended_title, title_variations, and description opening MUST be Hindi (Devanagari)\n"
                "- tags may mix Hindi and romanized Hindi keywords for search\n"
            )

        prompt = f"""Create YouTube SEO metadata for an original story video.
Language: {language}
Title: {story.get("title")}
Synopsis: {story.get("synopsis")}
Topic research: {research}

Rules:
{hindi_rule}
- Natural keyword use, no stuffing
- 5 title variations (max 95 chars), pick one recommended
- Description with hooks and chapters if long-form
- 15-25 relevant tags
- Hashtags (3-8)
- Category ID (YouTube numeric string, e.g. 24 Entertainment)
- Playlist name suggestion

JSON schema:
{{
  "main_topic": "...",
  "keywords": ["..."],
  "long_tail_keywords": ["..."],
  "title_variations": ["..."],
  "recommended_title": "...",
  "description": "...",
  "tags": ["..."],
  "hashtags": ["..."],
  "category_id": "24",
  "playlist_suggestion": "...",
  "chapters": [{{"time": "00:00", "title": "..."}}]
}}"""

        response = self.llm.complete(prompt, system="Output JSON only.", json_mode=True)
        return self.llm.parse_json(response.text)

    def generate_full_package(
        self,
        story: dict[str, Any],
        language: str,
        *,
        category_id: str,
        topic_research: dict[str, Any],
        thumbnail_text: str | None = None,
    ) -> dict[str, Any]:
        base = self.generate(story, language)
        titles = base.get("title_variations") or []
        if len(titles) < 5:
            titles = titles + [base.get("recommended_title", "")] * (5 - len(titles))

        prompt = f"""You are a Hindi YouTube creative manager.
Category: {category_id}
Story title: {story.get("title")}
Synopsis: {story.get("synopsis")}
Research: {topic_research}
Thumbnail text: {thumbnail_text or ""}

Create promotional copy. Hindi Devanagari. No false claims. JSON:
{{
  "title_selection_reason": "...",
  "promotional_caption": "short social caption with curiosity",
  "pinned_comment": "one discussion question about the story",
  "hashtags_text": "#tag1 #tag2 ...",
  "seo_report": {{
    "primary_keyword": "...",
    "secondary_keywords": ["..."],
    "search_intent": "...",
    "audience_fit": "...",
    "competition_note": "..."
  }}
}}"""
        extra = self.llm.complete(prompt, system="Valid JSON only.", json_mode=True)
        extra_data = self.llm.parse_json(extra.text)

        return {
            **base,
            "title_variations": titles[:5],
            "title_selection_reason": extra_data.get("title_selection_reason"),
            "promotional_caption": extra_data.get("promotional_caption"),
            "pinned_comment": extra_data.get("pinned_comment"),
            "hashtags_text": extra_data.get("hashtags_text"),
            "seo_report": extra_data.get("seo_report"),
            "selected_title": base.get("recommended_title"),
        }
