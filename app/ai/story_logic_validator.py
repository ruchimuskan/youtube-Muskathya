from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class LogicValidationIssue:
    severity: str  # "critical", "warning", "info"
    category: str
    scene_number: int | None
    description: str
    recommendation: str


@dataclass
class LogicValidationReport:
    is_valid: bool
    issues: list[LogicValidationIssue] = field(default_factory=list)
    critical_count: int = 0
    warning_count: int = 0
    continuity_score: int = 10  # 1 to 10 scale


class StoryLogicValidator:
    """
    Validates Bollywood screenplay continuity, setups and payoffs,
    character consistency, and logical cause-and-effect chains.
    """

    def __init__(self) -> None:
        pass

    def validate(self, story: dict[str, Any], blueprint: dict[str, Any] | None = None) -> LogicValidationReport:
        issues: list[LogicValidationIssue] = []
        scenes = story.get("scenes") or []
        is_short = bool(story.get("is_short"))

        # 1. Scene count check
        min_scenes = 4 if is_short else 8
        if len(scenes) < min_scenes:
            issues.append(
                LogicValidationIssue(
                    severity="critical",
                    category="scene_count",
                    scene_number=None,
                    description=f"Story has only {len(scenes)} scenes (minimum required: {min_scenes}).",
                    recommendation="Expand the story with concrete intermediate investigation/conflict scenes.",
                )
            )

        # 2. Character Cast & Unknown Speakers Check
        characters = story.get("characters") or []
        char_names = {c.get("name") for c in characters if isinstance(c, dict) and c.get("name")}
        allowed_generic_speakers = {"Narrator", "सूत्रधार", "वॉइसओवर", "Voiceover", "पात्र", "अजनबी", "भीड़"}

        used_speakers: dict[str, list[int]] = {}
        for sc in scenes:
            sn = sc.get("scene_number", 0)
            for d in sc.get("dialogue") or []:
                if isinstance(d, dict):
                    spk = (d.get("character") or "").strip()
                    if spk:
                        used_speakers.setdefault(spk, []).append(sn)

        for spk, appearances in used_speakers.items():
            if spk not in char_names and spk not in allowed_generic_speakers:
                # If speaker only appears in the very last scene or climax without introduction
                if all(sn >= len(scenes) - 1 for sn in appearances):
                    issues.append(
                        LogicValidationIssue(
                            severity="critical",
                            category="unexplained_deus_ex_machina",
                            scene_number=appearances[0],
                            description=f"Speaker '{spk}' suddenly appears at the climax without prior setup.",
                            recommendation=f"Introduce '{spk}' or foreshadow their arrival in early scenes.",
                        )
                    )
                else:
                    issues.append(
                        LogicValidationIssue(
                            severity="warning",
                            category="unregistered_character",
                            scene_number=appearances[0],
                            description=f"Speaker '{spk}' is not defined in characters cast list.",
                            recommendation=f"Add '{spk}' to story.characters with visual details.",
                        )
                    )

        # 3. Setup and Payoff (Clues & Mystery Resolution)
        if blueprint and isinstance(blueprint, dict):
            hidden_clues = blueprint.get("hidden_clues") or []
            # Check if planted clues appear in story narration
            full_story_text = " ".join(sc.get("narration", "") for sc in scenes)
            for clue_item in hidden_clues:
                if isinstance(clue_item, dict):
                    clue_text = clue_item.get("clue", "")
                    # Extract key nouns/words from clue
                    words = [w for w in re.findall(r"[\u0900-\u097F\w]+", clue_text) if len(w) > 4]
                    if words and not any(w in full_story_text for w in words):
                        issues.append(
                            LogicValidationIssue(
                                severity="warning",
                                category="unplanted_clue",
                                scene_number=clue_item.get("planted_in_scene"),
                                description=f"Planted clue '{clue_text[:40]}...' from blueprint not found in story scenes.",
                                recommendation="Explicitly mention and describe this physical clue during investigation.",
                            )
                        )

        # 4. Abrupt Ending & Incomplete Resolution Check
        ending = (story.get("ending") or "").strip()
        last_scene_narr = (scenes[-1].get("narration") if scenes else "") or ""
        combined_ending = ending + " " + last_scene_narr

        if len(combined_ending.strip()) < 80:
            issues.append(
                LogicValidationIssue(
                    severity="critical",
                    category="incomplete_ending",
                    scene_number=len(scenes),
                    description="Story ending is too abrupt or lacks concrete final resolution.",
                    recommendation="Show the exact fate of the protagonist and antagonist in a detailed final scene.",
                )
            )

        # Cop-out endings check
        cop_out_phrases = [
            "सब कुछ ठीक हो गया",
            "जिंदगी बदल गई",
            "यही सच्चाई है",
            "समय बीतता गया",
        ]
        for cop in cop_out_phrases:
            if cop in ending and len(ending) < 120:
                issues.append(
                    LogicValidationIssue(
                        severity="critical",
                        category="cop_out_ending",
                        scene_number=len(scenes),
                        description=f"Ending relies on vague cop-out phrase '{cop}'.",
                        recommendation="Show the physical resolution, legal outcome, or emotional realization.",
                    )
                )
                break

        # Calculate scores
        critical_count = sum(1 for iss in issues if iss.severity == "critical")
        warning_count = sum(1 for iss in issues if iss.severity == "warning")
        continuity_score = max(1, 10 - (critical_count * 3) - (warning_count * 1))

        is_valid = critical_count == 0

        return LogicValidationReport(
            is_valid=is_valid,
            issues=issues,
            critical_count=critical_count,
            warning_count=warning_count,
            continuity_score=continuity_score,
        )
