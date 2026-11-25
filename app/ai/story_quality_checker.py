from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from typing import Any

from app.ai.providers import LLMRouter

logger = logging.getLogger(__name__)


@dataclass
class QualityDimension:
    name: str
    weight: int
    score: int
    feedback: str


@dataclass
class StoryQualityReport:
    passed: bool
    total_score: int
    minimum_required: int
    dimensions: dict[str, int] = field(default_factory=dict)
    weak_sections: list[dict[str, Any]] = field(default_factory=list)
    critical_issues: list[str] = field(default_factory=list)
    feedback_for_rewrite: str = ""
    evaluation_method: str = "hybrid"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class StoryQualityChecker:
    """
    Strict 10-dimension story quality evaluator for Hindi cinematic YouTube stories.
    Enforces a minimum passing score of 85/100 before publication.
    """

    MIN_PASSING_SCORE: int = 85

    DIMENSION_KEYS = [
        "opening_hook",
        "character_consistency",
        "plot_logic_continuity",
        "suspense_escalation",
        "emotional_engagement",
        "twist_quality",
        "climax_impact",
        "ending_completeness",
        "hindi_grammar_dialogue",
        "anti_repetition",
    ]

    REPETITIVE_KEYWORDS = {
        "यह क्या है",
        "यह क्या हो रहा है",
        "तुम कौन हो",
        "यह क्या मतलब है",
        "तुम्हें कुछ नहीं पता",
        "क्या हुआ",
        "मुझे कुछ समझ नहीं आ रहा",
    }

    def __init__(self, llm: LLMRouter | None = None) -> None:
        self.llm = llm or LLMRouter()

    def evaluate(self, story: dict[str, Any]) -> StoryQualityReport:
        """
        Runs programmatic heuristics and LLM semantic validation to grade the story.
        """
        scenes = story.get("scenes") or []
        if not scenes:
            return StoryQualityReport(
                passed=False,
                total_score=0,
                minimum_required=self.MIN_PASSING_SCORE,
                critical_issues=["Story has zero scenes."],
                feedback_for_rewrite="Generate a complete story with at least 15 scenes.",
            )

        # 1. Programmatic Rule-based Diagnostics
        rule_scores, weak_sections, critical_issues = self._run_rule_diagnostics(story)

        # 2. Semantic LLM Scoring (if LLM is available)
        llm_scores: dict[str, int] = {}
        llm_feedback = ""
        try:
            llm_result = self._evaluate_with_llm(story, rule_scores, weak_sections)
            llm_scores = llm_result.get("scores", {})
            llm_feedback = llm_result.get("feedback", "")
            eval_method = "llm_validated"
        except Exception as exc:
            logger.warning("LLM story quality evaluation skipped (%s); using deterministic rule scoring", exc)
            eval_method = "rule_based"

        # Combine scores (LLM weighted 70%, rules 30% when LLM present, else 100% rules)
        final_dimensions: dict[str, int] = {}
        total = 0
        for dim in self.DIMENSION_KEYS:
            r_val = rule_scores.get(dim, 7)
            if dim in llm_scores:
                comb = int(round(llm_scores[dim] * 0.7 + r_val * 0.3))
            else:
                comb = r_val
            comb = max(1, min(10, comb))
            final_dimensions[dim] = comb
            total += comb

        passed = (total >= self.MIN_PASSING_SCORE) and (len(critical_issues) == 0)

        # Compile feedback
        feedback_lines = []
        if critical_issues:
            feedback_lines.append("CRITICAL FLAWS: " + "; ".join(critical_issues))
        if weak_sections:
            feedback_lines.append(
                "WEAK SCENES: " + "; ".join(f"Scene {w['scene_number']} ({w['issue']})" for w in weak_sections[:4])
            )
        if llm_feedback:
            feedback_lines.append("ACTIONABLE ADVICE: " + llm_feedback)

        report = StoryQualityReport(
            passed=passed,
            total_score=total,
            minimum_required=self.MIN_PASSING_SCORE,
            dimensions=final_dimensions,
            weak_sections=weak_sections,
            critical_issues=critical_issues,
            feedback_for_rewrite="\n".join(feedback_lines),
            evaluation_method=eval_method,
        )
        logger.info(
            "Story quality evaluation finished: score=%s/100 (min=%s), passed=%s",
            total,
            self.MIN_PASSING_SCORE,
            passed,
        )
        return report

    def _run_rule_diagnostics(
        self, story: dict[str, Any]
    ) -> tuple[dict[str, int], list[dict[str, Any]], list[str]]:
        scenes = story.get("scenes", [])
        total_scenes = len(scenes)
        is_short = bool(story.get("is_short"))
        critical_issues: list[str] = []
        weak_sections: list[dict[str, Any]] = []

        scores: dict[str, int] = {k: 8 for k in self.DIMENSION_KEYS}

        # 1. Scene count & duration depth check
        min_expected = 4 if is_short else 8
        if total_scenes < min_expected:
            critical_issues.append(f"Insufficient scene count ({total_scenes} < {min_expected})")
            scores["plot_logic_continuity"] = max(3, scores["plot_logic_continuity"] - 4)

        # 2. Hook check (Scene 1)
        if scenes:
            s1 = scenes[0]
            s1_narr = s1.get("narration") or ""
            s1_diag = " ".join(d.get("line", "") for d in s1.get("dialogue", []))
            s1_text = s1_narr + " " + s1_diag
            # Check for boring openings
            boring_starts = ["एक बार की बात", "एक गाँव में", "एक समय की बात", "किसी गाँव में"]
            if any(b in s1_text for b in boring_starts):
                scores["opening_hook"] = 4
                weak_sections.append({"scene_number": 1, "issue": "Generic fairytale start; needs a shocking cold hook"})
            elif len(s1_text) < 120:
                scores["opening_hook"] = 5
                weak_sections.append({"scene_number": 1, "issue": "Opening hook is too brief to build curiosity"})
            else:
                scores["opening_hook"] = 9

        # 3. Anti-repetition check
        all_narr_sentences: list[str] = []
        all_dialogue_lines: list[str] = []
        short_scene_count = 0

        for sc in scenes:
            sn = sc.get("scene_number", 0)
            narr = (sc.get("narration") or "").strip()
            if len(narr) < 140 and not is_short:
                short_scene_count += 1
                weak_sections.append({"scene_number": sn, "issue": "Narration too short or lacking atmospheric tension"})

            for d in sc.get("dialogue") or []:
                line = (d.get("line") or "").strip()
                if line:
                    all_dialogue_lines.append(line)
                    # Check for generic question loop
                    for kw in self.REPETITIVE_KEYWORDS:
                        if kw in line:
                            scores["anti_repetition"] = max(4, scores["anti_repetition"] - 1)
                            weak_sections.append(
                                {"scene_number": sn, "issue": f"Repetitive dialogue detected: '{kw}'"}
                            )
                            break

        if short_scene_count > total_scenes * 0.3:
            scores["suspense_escalation"] = max(4, scores["suspense_escalation"] - 3)
            critical_issues.append("Over 30% of scenes have superficial 1-2 sentence narrations")

        # Duplicate dialogues count
        unique_dialogues = set(all_dialogue_lines)
        if all_dialogue_lines and len(unique_dialogues) < len(all_dialogue_lines) * 0.8:
            scores["anti_repetition"] = max(3, scores["anti_repetition"] - 4)
            critical_issues.append("High duplicate dialogue frequency across scenes")

        # 4. Character consistency check
        char_refs = story.get("characters") or []
        char_names = {c.get("name") for c in char_refs if c.get("name")}
        used_dialogue_speakers = {
            d.get("character") for sc in scenes for d in sc.get("dialogue", []) if d.get("character")
        }
        unknown_speakers = used_dialogue_speakers - char_names - {"Narrator", "सूत्रधार", "पात्र", "अजनबी"}
        if len(unknown_speakers) > 2:
            scores["character_consistency"] = max(5, scores["character_consistency"] - 2)
            weak_sections.append(
                {"scene_number": 0, "issue": f"Characters appearing in dialogue not defined in cast: {unknown_speakers}"}
            )

        # 5. Climax & Ending completeness check
        if scenes:
            last_scene = scenes[-1]
            last_narr = last_scene.get("narration") or ""
            ending_text = story.get("ending") or ""
            full_ending = last_narr + " " + ending_text
            if len(full_ending.strip()) < 100:
                scores["ending_completeness"] = 4
                critical_issues.append("Abrupt or incomplete story ending")
                weak_sections.append({"scene_number": total_scenes, "issue": "Ending lacks proper resolution"})
            else:
                scores["ending_completeness"] = 9
                scores["climax_impact"] = 9

        return scores, weak_sections, critical_issues

    def _evaluate_with_llm(
        self,
        story: dict[str, Any],
        rule_scores: dict[str, int],
        weak_sections: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Calls LLM to score the story as a Bollywood Screenwriter & Script Doctor.
        """
        scenes = story.get("scenes", [])
        synopsis = story.get("synopsis", "")
        title = story.get("title", "")
        ending = story.get("ending", "")

        # Provide representative summary of story beats
        beat_summary = []
        for sc in scenes:
            sn = sc.get("scene_number", 0)
            beat = sc.get("story_beat", "scene")
            narr = (sc.get("narration") or "")[:200]
            diags = " | ".join(f"{d.get('character')}: {d.get('line')}" for d in sc.get("dialogue", [])[:2])
            beat_summary.append(f"Scene {sn} [{beat}]: {narr}\n  Dialogue: {diags}")

        prompt = f"""You are an elite Bollywood Screenplay Consultant and YouTube Audience Retention Specialist.
Audit the following Hindi story script across 10 critical storytelling dimensions.

Story Title: {title}
Synopsis: {synopsis}
Ending Resolution: {ending}

Story Scenes:
{chr(10).join(beat_summary[:18])}

Grade EACH dimension from 1 to 10 (10 = masterpiece Bollywood thriller level, 1 = unwatchable garbage).
CRITERIA (10 dimensions):
1. opening_hook (Must start within 10s with shock/mystery, NO boring introductions)
2. character_consistency (Distinct believable Indian characters with consistent names, traits, and stakes)
3. plot_logic_continuity (Strict cause-and-effect, no random disconnected incidents)
4. suspense_escalation (Tension rises every 30-45s with gradual clue reveals)
5. emotional_engagement (Real human stakes, deep emotional dilemma)
6. twist_quality (Shocking yet logically supported by earlier hints)
7. climax_impact (High-tension confrontation resolving the central mystery)
8. ending_completeness (100% complete, fully resolved, no abrupt cuts)
9. hindi_grammar_dialogue (Colloquial natural Hindi dialogue, no English transliteration, no speaker labels in spoken text)
10. anti_repetition (Zero recycled dialogue lines or question loops)

Output valid JSON ONLY in this exact format:
{{
  "scores": {{
    "opening_hook": 9,
    "character_consistency": 8,
    "plot_logic_continuity": 9,
    "suspense_escalation": 8,
    "emotional_engagement": 9,
    "twist_quality": 8,
    "climax_impact": 9,
    "ending_completeness": 9,
    "hindi_grammar_dialogue": 9,
    "anti_repetition": 9
  }},
  "total_score": 87,
  "feedback": "Short 1-2 sentence actionable advice to polish this story."
}}"""
        resp = self.llm.complete(prompt, system="You are an uncompromising screenplay judge. Output JSON only.", json_mode=True)
        return self.llm.parse_json(resp.text)
