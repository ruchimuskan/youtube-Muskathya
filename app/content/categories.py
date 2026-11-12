from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ContentCategory:
    id: str
    name_hi: str
    name_en: str
    legacy_genre: str
    default_weight: float
    audience: str
    story_style: str
    visual_style: str
    voice_profile: str
    audio_profile: str
    thumbnail_tone: str
    kids_safe: bool = False


CATEGORIES: dict[str, ContentCategory] = {
    "moral": ContentCategory(
        id="moral",
        name_hi="नैतिक कहानियाँ",
        name_en="Moral Stories",
        legacy_genre="moral",
        default_weight=0.20,
        audience="family",
        story_style=(
            "Relatable Indian characters, clear moral problem, emotional resolution, "
            "lesson through story not preaching. Simple natural Hindi."
        ),
        visual_style="warm cinematic Indian illustration, relatable everyday setting",
        voice_profile="moral",
        audio_profile="moral",
        thumbnail_tone="hopeful, clear emotion on face",
    ),
    "horror_mystery": ContentCategory(
        id="horror_mystery",
        name_hi="डरावनी और रहस्यमयी कहानियाँ",
        name_en="Horror and Mystery",
        legacy_genre="horror",
        default_weight=0.15,
        audience="adult_teens",
        story_style=(
            "Strong suspense hook, gradual tension, atmospheric mystery, satisfying reveal. "
            "No graphic gore; psychological horror acceptable. Hindi suspense narration."
        ),
        visual_style="dark atmospheric cinematic, moonlight, fog, shadows, moody colors",
        voice_profile="horror",
        audio_profile="horror",
        thumbnail_tone="mystery, fear, high contrast",
    ),
    "emotional_family": ContentCategory(
        id="emotional_family",
        name_hi="भावनात्मक और पारिवारिक कहानियाँ",
        name_en="Emotional and Family",
        legacy_genre="family",
        default_weight=0.15,
        audience="family",
        story_style="Strong relationships, natural dialogue, heartfelt moments, meaningful ending.",
        visual_style="soft emotional lighting, Indian home or family scenes",
        voice_profile="emotional",
        audio_profile="emotional",
        thumbnail_tone="tears or embrace, warm colors",
    ),
    "inspirational": ContentCategory(
        id="inspirational",
        name_hi="प्रेरणादायक कहानियाँ",
        name_en="Inspirational",
        legacy_genre="motivational",
        default_weight=0.10,
        audience="young_adult",
        story_style="Relatable struggle, character growth, realistic motivation, no fake claims.",
        visual_style="uplifting sunrise, journey, determination",
        voice_profile="motivational",
        audio_profile="inspirational",
        thumbnail_tone="determination, upward gaze",
    ),
    "raja_rani_fantasy": ContentCategory(
        id="raja_rani_fantasy",
        name_hi="राजा-रानी और काल्पनिक कहानियाँ",
        name_en="Raja-Rani and Fantasy",
        legacy_genre="fantasy",
        default_weight=0.10,
        audience="family",
        story_style="Palace and kingdom, royal costumes, adventure conflict resolution, grand tone.",
        visual_style="Indian palace, royal attire, golden lighting, epic fantasy illustration",
        voice_profile="royal",
        audio_profile="royal",
        thumbnail_tone="crown, palace, drama",
    ),
    "kids_animal": ContentCategory(
        id="kids_animal",
        name_hi="बच्चों और जानवरों की कहानियाँ",
        name_en="Kids and Animal",
        legacy_genre="children",
        default_weight=0.10,
        audience="children",
        story_style="Simple Hindi, friendly tone, safe content, playful animals or kids heroes.",
        visual_style="bright colorful friendly illustration, jungle or farm",
        voice_profile="kids",
        audio_profile="kids",
        thumbnail_tone="cute, bright, friendly",
        kids_safe=True,
    ),
    "village_life": ContentCategory(
        id="village_life",
        name_hi="गाँव की कहानियाँ",
        name_en="Village Life",
        legacy_genre="village",
        default_weight=0.10,
        audience="family",
        story_style="Rural India, farmers, community, authentic village problems and wisdom.",
        visual_style="Indian village fields, huts, sunrise, earthy tones",
        voice_profile="moral",
        audio_profile="village",
        thumbnail_tone="village landscape, farmer",
    ),
    "folk_mythology": ContentCategory(
        id="folk_mythology",
        name_hi="लोक कथा और पौराणिक प्रेरणा",
        name_en="Folk and Mythology-inspired",
        legacy_genre="folklore",
        default_weight=0.05,
        audience="family",
        story_style=(
            "Original narration inspired by Indian folklore or mythology themes; "
            "not copying copyrighted retellings."
        ),
        visual_style="traditional Indian art inspired, temples, rivers, symbolic imagery",
        voice_profile="royal",
        audio_profile="folk",
        thumbnail_tone="traditional, symbolic",
    ),
    "suspense_thriller": ContentCategory(
        id="suspense_thriller",
        name_hi="सस्पेंस और थ्रिलर",
        name_en="Suspense Thriller",
        legacy_genre="suspense",
        default_weight=0.05,
        audience="adult",
        story_style="Fast pacing hooks, twists, cliffhanger beats, coherent reveal.",
        visual_style="high contrast thriller lighting, urban or night scenes",
        voice_profile="horror",
        audio_profile="thriller",
        thumbnail_tone="shock, secret",
    ),
    "fantasy_adventure": ContentCategory(
        id="fantasy_adventure",
        name_hi="काल्पनिक और रोमांचक",
        name_en="Fantasy Adventure",
        legacy_genre="adventure",
        default_weight=0.05,
        audience="teen",
        story_style="Quest, magical elements, action beats, wonder.",
        visual_style="epic adventure fantasy Indian landscape",
        voice_profile="royal",
        audio_profile="adventure",
        thumbnail_tone="action, magic",
    ),
    "life_lessons": ContentCategory(
        id="life_lessons",
        name_hi="जीवन की सीख और रिश्ते",
        name_en="Life Lessons",
        legacy_genre="relationships",
        default_weight=0.05,
        audience="adult",
        story_style="Relationships, choices, modern Indian life lessons.",
        visual_style="contemporary Indian settings, office or home",
        voice_profile="emotional",
        audio_profile="emotional",
        thumbnail_tone="conversation, choice",
    ),
    "indian_folk": ContentCategory(
        id="indian_folk",
        name_hi="भारतीय लोक कथाएँ",
        name_en="Indian Folk Tales",
        legacy_genre="folklore",
        default_weight=0.03,
        audience="family",
        story_style="Original folk-style tale with village wisdom.",
        visual_style="folk art aesthetic, storyteller circle",
        voice_profile="moral",
        audio_profile="folk",
        thumbnail_tone="storyteller",
    ),
    "mythology_inspired": ContentCategory(
        id="mythology_inspired",
        name_hi="पौराणिक प्रेरित",
        name_en="Mythology-inspired",
        legacy_genre="mythology",
        default_weight=0.02,
        audience="family",
        story_style="Inspired themes only; original characters and plot.",
        visual_style="divine lighting symbolic, not copying specific copyrighted depictions",
        voice_profile="royal",
        audio_profile="folk",
        thumbnail_tone="symbolic divine light",
    ),
}


def get_category(category_id: str) -> ContentCategory:
    if category_id not in CATEGORIES:
        return CATEGORIES["moral"]
    return CATEGORIES[category_id]


def all_category_ids() -> list[str]:
    return list(CATEGORIES.keys())


def category_story_block(category: ContentCategory) -> str:
    return f"""
Category: {category.name_hi} ({category.name_en})
Audience: {category.audience}
Story style: {category.story_style}
Visual style: {category.visual_style}
Safety: {"children-safe only" if category.kids_safe else "general audience, no graphic violence"}
"""


def format_duration_range(mode: str) -> tuple[int, int, int, int]:
    """Returns min_sec, max_sec, min_scenes, max_scenes."""
    if mode == "short":
        return 30, 60, 4, 6
    if mode == "extended":
        return 600, 900, 28, 45
    if mode == "compilation":
        return 600, 1200, 30, 50
    return 300, 480, 18, 32
