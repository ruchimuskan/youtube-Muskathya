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
- Optimize for Indian YouTube search + suggested feed: curiosity titles, emotional keywords
- Natural keyword use, no stuffing; mix Hindi + common romanized search terms in tags
- 5 title variations (max 95 chars), pick one recommended — highest CTR without misleading
- Description: first 2 lines = hook + main keyword; then story promise; chapters if long-form
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

        try:
            response = self.llm.complete(prompt, system="Output JSON only.", json_mode=True)
            return self.llm.parse_json(response.text)
        except Exception as exc:
            logger.warning("SEO generation LLM failed (%s). Using procedural SEO.", exc)
            title = story.get("title") or "हिंदी प्रेरक और रहस्यमयी कहानी"
            return {
                "main_topic": title,
                "keywords": ["hindi story", "kahaniya", "moral stories in hindi", "hindi kahaniya"],
                "long_tail_keywords": ["heart touching hindi story", "best hindi kahani 2026", "suspense kahani"],
                "title_variations": [
                    f"{title} | दिल छू लेने वाली हिंदी कहानी",
                    f"{title} - सच्ची घटना पर आधारित",
                    f"ज़रूर सुनें: {title} | Hindi Kahaniya",
                    f"{title} (एक अनोखी दास्तान)",
                    f"कर्मों का हिसाब: {title}",
                ],
                "recommended_title": f"{title} | दिल छू लेने वाली हिंदी कहानी",
                "description": f"{title}\n\n{story.get('synopsis', 'एक दिलचस्प और दिल को छू लेने वाली हिंदी कहानी।')}\n\nअगर आपको यह कहानी पसंद आए तो लाइक और सब्सक्राइब ज़रूर करें!\n\n#HindiKahaniya #MoralStories #HindiStories",
                "tags": ["hindi kahaniya", "hindi stories", "moral story", "kahani", "hindi kahani", "story in hindi"],
                "hashtags": ["#HindiKahaniya", "#HindiStories", "#Kahani", "#MoralStories"],
                "category_id": "24",
                "playlist_suggestion": "सर्वश्रेष्ठ हिंदी कहानियाँ",
                "chapters": [{"time": "00:00", "title": "कहानी की शुरुआत"}, {"time": "02:30", "title": "रहस्य और मोड़"}, {"time": "05:00", "title": "सीख और अंत"}],
            }

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
        try:
            extra = self.llm.complete(prompt, system="Valid JSON only.", json_mode=True)
            extra_data = self.llm.parse_json(extra.text)
        except Exception as exc:
            logger.warning("Creative SEO LLM failed (%s). Using base SEO copy.", exc)
            extra_data = {
                "title_selection_reason": "High CTR emotional hook",
                "promotional_caption": f"सुनिए {story.get('title')} की यह अनोखी दास्तान...",
                "pinned_comment": "आपको इस कहानी में कौन सा पात्र सबसे अच्छा लगा? कमेंट में ज़रूर बताएं!",
                "hashtags_text": "#HindiKahaniya #HindiStories #StoriesInHindi",
                "seo_report": {
                    "primary_keyword": "hindi kahaniya",
                    "secondary_keywords": ["moral story", "hindi story"],
                    "search_intent": "Audience looking for emotional life lessons",
                    "audience_fit": "General Hindi storytelling audience",
                    "competition_note": "Authentic narrative structure",
                },
            }

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
