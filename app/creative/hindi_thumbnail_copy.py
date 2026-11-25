from __future__ import annotations

import re
from typing import Any

# Approved overlay copy for mythological specific stories
SHIVA_GANESHA_HEADLINE = "शिव जी का अनमोल उपहार!"
SHIVA_GANESHA_SUSPENSE = "गणेश जी को क्या मिला?"

MARKDOWN_RE = re.compile(r"[*#_`~\[\]]+")

CURIOUS_HOOK_POOL = [
    "आखिर सच क्या था?",
    "आधी रात का राज!",
    "उस कमरे में कौन था?",
    "20 साल पुराना रहस्य",
    "जिस पर भरोसा किया...",
    "खौफ़नाक मंज़र का सच",
    "बंद दरवाज़े के पीछे!",
    "अंतिम खत का खुलासा",
    "धोखे की असली वजह",
    "अनसुनी चीख का राज",
]


def sanitize_hindi(text: str) -> str:
    text = MARKDOWN_RE.sub("", text or "")
    text = text.replace("**", "").strip()
    return re.sub(r"\s+", " ", text).strip()


def is_valid_devanagari_headline(text: str) -> bool:
    text = sanitize_hindi(text)
    if not text or len(text) < 3:
        return False
    devanagari = sum(1 for c in text if "\u0900" <= c <= "\u097f")
    # Must have solid Devanagari presence and no English words
    has_english = bool(re.search(r"[a-zA-Z]", text))
    if has_english:
        return False
    return devanagari >= max(3, len(text) // 3)


def enforce_short_headline(text: str, max_words: int = 5) -> str:
    """Enforces 2 to 5 words for punchy mobile readability."""
    words = sanitize_hindi(text).split()
    if not words:
        return "आखिर सच क्या था?"
    if len(words) <= max_words:
        return " ".join(words)
    return " ".join(words[:max_words])


def derive_story_curiosity_hook(story: dict[str, Any]) -> str:
    """Derives an original 2-5 word curiosity hook based on the actual story content."""
    title = (story.get("title") or "").strip()
    synopsis = (story.get("synopsis") or "").strip()
    scenes = story.get("scenes") or []
    full_context = f"{title} {synopsis} " + " ".join(s.get("narration", "")[:100] for s in scenes[:3])

    if "खत" in full_context or "चिट्ठी" in full_context:
        return "उस खत का सच!"
    if "कमरे" in full_context or "तहखाने" in full_context:
        return "उस कमरे में कौन था?"
    if "हवेली" in full_context or "खंडहर" in full_context:
        return "हवेली का काला सच!"
    if "आधी रात" in full_context or "रात" in full_context:
        return "आधी रात का राज!"
    if "खून" in full_context or "साजिश" in full_context or "धोखा" in full_context:
        return "जिस पर भरोसा किया..."
    if "20 साल" in full_context or "बरसों" in full_context:
        return "20 साल पुराना रहस्य"

    if title:
        short = enforce_short_headline(title.split("|")[0].split("-")[0].strip(), max_words=4)
        if is_valid_devanagari_headline(short) and len(short.split()) >= 2:
            return short

    return "आखिर सच क्या था?"


def resolve_overlay_text(
    story: dict[str, Any], category_id: str, analysis: dict[str, Any] | None = None
) -> tuple[str, str, bool]:
    """
    Returns (headline, suspense, locked).
    headline: 2-5 word curiosity hook.
    suspense: optional 2-4 word supporting punchline.
    """
    from app.creative.thumbnail_character_bible import story_has_shiva_ganesha

    if story_has_shiva_ganesha(story):
        return SHIVA_GANESHA_HEADLINE, SHIVA_GANESHA_SUSPENSE, True

    analysis = analysis or {}
    raw_head = sanitize_hindi(analysis.get("hindi_headline") or "")
    suspense = sanitize_hindi(analysis.get("hindi_suspense") or "")

    if is_valid_devanagari_headline(raw_head) and len(raw_head.split()) >= 2:
        headline = enforce_short_headline(raw_head, max_words=5)
    else:
        headline = derive_story_curiosity_hook(story)

    if suspense and (not is_valid_devanagari_headline(suspense) or len(suspense.split()) > 5):
        suspense = ""

    return headline, suspense, False
