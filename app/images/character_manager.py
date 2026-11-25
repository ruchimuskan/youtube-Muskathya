from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class CharacterProfile:
    name: str
    gender: str
    age_group: str
    physical_appearance: str
    signature_attire: str
    personality: str
    base_seed: int


class CharacterManager:
    """
    Maintains cross-scene visual consistency for characters.
    Extracts or creates persistent character reference profiles, ensures stable deterministic seeds,
    and injects exact facial and clothing anchors into scene image prompts.
    """

    CINEMATIC_BOLLYWOOD_STYLE: str = (
        "ultra-realistic cinematic photography, 35mm film still, photorealistic Bollywood thriller cinematography, "
        "dramatic atmospheric lighting, shallow depth of field, natural human skin texture, authentic Indian setting, 8k"
    )

    def __init__(self, story: dict[str, Any]) -> None:
        self.story = story
        self.settings = get_settings()
        self.story_id = story.get("story_project_id", 101)
        self.profiles: dict[str, CharacterProfile] = self._build_character_sheet()

    def _build_character_sheet(self) -> dict[str, CharacterProfile]:
        profiles = {}
        raw_chars = self.story.get("characters") or []
        char_refs = self.story.get("character_references") or []
        ref_lookup = {c.get("name"): c for c in char_refs if isinstance(c, dict)}

        for c in raw_chars:
            if not isinstance(c, dict):
                continue
            name = (c.get("name") or "Character").strip()
            gender = c.get("gender") or "male"
            age = c.get("age_group") or "late 20s"

            ref = ref_lookup.get(name, {})
            phys = (
                ref.get("physical_appearance")
                or c.get("description")
                or f"Sharp natural Indian features, intense dark eyes, styled black hair, realistic {gender}"
            )
            attire = (
                ref.get("signature_attire")
                or "Authentic contemporary Indian clothing with textured fabric"
            )
            personality = ref.get("personality") or "observant and intense"

            seed = self.character_seed(name, self.story_id)
            profiles[name] = CharacterProfile(
                name=name,
                gender=gender,
                age_group=age,
                physical_appearance=phys,
                signature_attire=attire,
                personality=personality,
                base_seed=seed,
            )

        return profiles

    def get_characters_in_scene(self, scene: dict[str, Any]) -> list[CharacterProfile]:
        """Identifies characters appearing in the given scene."""
        explicit = scene.get("characters_present") or []
        found: list[CharacterProfile] = []

        if explicit:
            for name in explicit:
                if name in self.profiles:
                    found.append(self.profiles[name])

        if not found:
            # Check dialogue speakers
            for d in scene.get("dialogue") or []:
                speaker = d.get("character")
                if speaker and speaker in self.profiles and self.profiles[speaker] not in found:
                    found.append(self.profiles[speaker])

        if not found:
            # Check narration mentions
            narr = scene.get("narration") or ""
            for name, prof in self.profiles.items():
                if name in narr:
                    found.append(prof)

        if not found and self.profiles:
            # Default to lead character
            found.append(next(iter(self.profiles.values())))

        return found

    def scene_prompt(self, scene: dict[str, Any]) -> str:
        """Constructs a detailed cinematic SDXL prompt anchored to character reference sheets."""
        base_visual = (scene.get("visual_description") or scene.get("image_prompt") or "").strip()
        mood = scene.get("mood") or "suspense"
        active_chars = self.get_characters_in_scene(scene)

        char_clauses = []
        for char in active_chars[:2]:
            clause = (
                f"character {char.name} ({char.age_group} Indian {char.gender}, {char.physical_appearance}, "
                f"wearing {char.signature_attire})"
            )
            char_clauses.append(clause)

        char_block = "; ".join(char_clauses)
        style = self.story.get("visual_style") or self.CINEMATIC_BOLLYWOOD_STYLE

        prompt = (
            f"{style}. "
            f"Scene event: {base_visual}. "
            f"Mood: {mood}. "
        )
        if char_block:
            prompt += f"Visual consistency: {char_block}. "

        prompt += (
            "single clear focal subject, hyperrealistic Bollywood movie still, atmospheric volumetrics, "
            "no text, no watermark, no duplicate faces, no cartoon, 16:9 widescreen composition."
        )
        return prompt[:380]

    def character_seed(self, key: str, story_seed: int = 42) -> int:
        """Deterministic pseudo-random seed guaranteed stable across Python restarts."""
        payload = f"{story_seed}_{key}".encode("utf-8")
        h = hashlib.sha256(payload).hexdigest()
        return int(h[:8], 16) % (2**31 - 1)

    def export_character_sheet(self) -> list[dict[str, Any]]:
        return [
            {
                "name": p.name,
                "gender": p.gender,
                "age_group": p.age_group,
                "physical_appearance": p.physical_appearance,
                "signature_attire": p.signature_attire,
                "personality": p.personality,
                "base_seed": p.base_seed,
            }
            for p in self.profiles.values()
        ]
