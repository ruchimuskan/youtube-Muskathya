from __future__ import annotations

import re
from typing import Any

# Approved overlay copy (never from image model; Pillow only)
SHIVA_GANESHA_HEADLINE = "शिव जी का अनमोल उपहार!"
SHIVA_GANESHA_SUSPENSE = "गणेश जी को क्या मिला?"

MARKDOWN_RE = re.compile(r"[*#_`~\[\]]+")


def sanitize_hindi(text: str) -> str:
    text = MARKDOWN_RE.sub("", text or "")
    text = text.replace("**", "").strip()
    return re.sub(r"\s+", " ", text).strip()


def is_valid_devanagari_headline(text: str) -> bool:
    text = sanitize_hindi(text)
    if not text or len(text) < 3:
        return False
    devanagari = sum(1 for c in text if "\u0900" <= c <= "\u097f")
    return devanagari >= max(3, len(text) // 3)


def resolve_overlay_text(
    story: dict[str, Any], category_id: str, analysis: dict[str, Any] | None = None
) -> tuple[str, str, bool]:
    """
    Returns (headline, suspense, locked).
    locked=True means do not use LLM rewrites (curated CTR copy).
    """
    from app.creative.thumbnail_character_bible import story_has_shiva_ganesha

    if story_has_shiva_ganesha(story):
        return SHIVA_GANESHA_HEADLINE, SHIVA_GANESHA_SUSPENSE, True

    analysis = analysis or {}
    headline = sanitize_hindi(analysis.get("hindi_headline") or "")
    suspense = sanitize_hindi(analysis.get("hindi_suspense") or "")

    if not is_valid_devanagari_headline(headline):
        title = sanitize_hindi(story.get("title") or "रोमांचक कहानी")
        words = title.split()
        headline = " ".join(words[:6])
        if len(headline) > 42:
            headline = headline[:42].rsplit(" ", 1)[0] + "…"

    if suspense and not is_valid_devanagari_headline(suspense):
        suspense = ""

    return headline, suspense, False
