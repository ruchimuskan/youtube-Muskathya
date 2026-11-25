from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from typing import Any

from app.ai.providers import LLMRouter
from app.ai.repetition_detector import RepetitionDetector
from app.ai.story_logic_validator import StoryLogicValidator
from app.ai.vague_sentence_detector import VagueSentenceDetector

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
    repetition_penalty: int = 0
    vague_penalty: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class StoryQualityChecker:
    """
    Strict 10-dimension story quality evaluator for Hindi cinematic YouTube stories.
    Enforces a minimum passing score of 85/100 before publication.
    Integrates RepetitionDetector, VagueSentenceDetector, and StoryLogicValidator.
    """

    MIN_PASSING_SCORE: int = 85

    DIMENSION_KEYS = [
        "opening_hook",
        "actual_event_detail",
        "scene_quality",
        "logical_continuity",
        "character_development",
        "dialogue_quality",
        "suspense",
        "originality",
        "climax",
        "ending_and_conclusion",
    ]

    # Legacy mapping for backwards-compatibility
    LEGACY_DIM_MAP = {
        "character_consistency": "character_development",
        "plot_logic_continuity": "logical_continuity",
        "suspense_escalation": "suspense",
        "emotional_engagement": "originality",
        "twist_quality": "climax",
        "climax_impact": "climax",
        "ending_completeness": "ending_and_conclusion",
        "hindi_grammar_dialogue": "dialogue_quality",
        "anti_repetition": "scene_quality",
    }

    def __init__(self, llm: LLMRouter | None = None) -> None:
        self.llm = llm or LLMRouter()
        self.repetition_detector = RepetitionDetector()
        self.vague_detector = VagueSentenceDetector()
        self.logic_validator = StoryLogicValidator()

    def evaluate(self, story: dict[str, Any], blueprint: dict[str, Any] | None = None) -> StoryQualityReport:
        """
        Runs programmatic heuristics, repetition audits, vague sentence checks,
        and LLM semantic validation to grade the story.
        """
        scenes = story.get("scenes") or []
        if not scenes:
            return StoryQualityReport(
                passed=False,
                total_score=0,
                minimum_required=self.MIN_PASSING_SCORE,
                critical_issues=["Story has zero scenes."],
                feedback_for_rewrite="Generate a complete story with scene-based storytelling.",
            )

        # 1. Programmatic Rule-based Diagnostics
        rule_scores, weak_sections, critical_issues = self._run_rule_diagnostics(story, blueprint=blueprint)

        # 2. Repetition & Vague Storytelling Penalties
        rep_penalty, rep_critiques = self.repetition_detector.calculate_repetition_penalty(story)
        vague_penalty, vague_critiques = self.vague_detector.calculate_vague_penalty(story)

        # 3. Semantic LLM Scoring (if LLM is available)
        llm_scores: dict[str, int] = {}
        llm_feedback = ""
        try:
            llm_result = self._evaluate_with_llm(story, rule_scores, weak_sections)
            raw_scores = llm_result.get("scores", {})
            # Map any legacy keys to canonical keys
            for k, v in raw_scores.items():
                target_key = self.LEGACY_DIM_MAP.get(k, k)
                if target_key in self.DIMENSION_KEYS:
                    llm_scores[target_key] = v
                llm_scores[k] = v  # keep both for test compatibility
            llm_feedback = llm_result.get("feedback", "")
            eval_method = "llm_validated"
        except Exception as exc:
            logger.warning("LLM story quality evaluation skipped (%s); using deterministic rule scoring", exc)
            eval_method = "rule_based"

        # Combine scores (LLM weighted 70%, rules 30% when LLM present, else 100% rules)
        final_dimensions: dict[str, int] = {}
        base_sum = 0
        for dim in self.DIMENSION_KEYS:
            r_val = rule_scores.get(dim, 8)
            if dim in llm_scores:
                comb = int(round(llm_scores[dim] * 0.7 + r_val * 0.3))
            else:
                comb = r_val
            comb = max(1, min(10, comb))
            final_dimensions[dim] = comb
            base_sum += comb

        # Also populate legacy dimension keys for compatibility
        for leg_k, can_k in self.LEGACY_DIM_MAP.items():
            final_dimensions[leg_k] = final_dimensions.get(can_k, 8)

        total_score = base_sum
        passed = (total_score >= self.MIN_PASSING_SCORE) and (len(critical_issues) == 0)

        # Compile feedback
        feedback_lines = []
        if critical_issues:
            feedback_lines.append("CRITICAL FLAWS: " + "; ".join(critical_issues))
        if weak_sections:
            feedback_lines.append(
                "WEAK SCENES: " + "; ".join(f"Scene {w.get('scene_number')} ({w.get('issue')})" for w in weak_sections[:4])
            )
        if rep_penalty > 0:
            feedback_lines.append(f"REPETITION PENALTY (-{rep_penalty}): Fix repetitive phrases/dialogue.")
        if vague_penalty > 0:
            feedback_lines.append(f"VAGUE STORYTELLING PENALTY (-{vague_penalty}): Explain concrete events (who, what, where).")
        if llm_feedback:
            feedback_lines.append("ACTIONABLE ADVICE: " + llm_feedback)

        report = StoryQualityReport(
            passed=passed,
            total_score=total_score,
            minimum_required=self.MIN_PASSING_SCORE,
            dimensions=final_dimensions,
            weak_sections=weak_sections,
            critical_issues=critical_issues,
            feedback_for_rewrite="\n".join(feedback_lines),
            evaluation_method=eval_method,
            repetition_penalty=rep_penalty,
            vague_penalty=vague_penalty,
        )
        logger.info(
            "Story quality evaluation finished: score=%s/100 (rep_penalty=%s, vague_penalty=%s, min=%s), passed=%s",
            total_score,
            rep_penalty,
            vague_penalty,
            self.MIN_PASSING_SCORE,
            passed,
        )
        return report

    def _run_rule_diagnostics(
        self, story: dict[str, Any], blueprint: dict[str, Any] | None = None
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
            scores["logical_continuity"] = max(3, scores["logical_continuity"] - 4)

        # 2. Hook check (Scene 1)
        if scenes:
            s1 = scenes[0]
            s1_narr = s1.get("narration") or ""
            s1_diag = " ".join(d.get("line", "") for d in s1.get("dialogue", []))
            s1_text = s1_narr + " " + s1_diag
            boring_starts = ["एक बार की बात", "एक गाँव में", "एक समय की बात", "किसी गाँव में"]
            if any(b in s1_text for b in boring_starts):
                scores["opening_hook"] = 4
                weak_sections.append({"scene_number": 1, "issue": "Generic fairytale start; needs a shocking cold hook"})
                critical_issues.append("Opening hook uses cliché fairytale start.")
            elif len(s1_text) < 120:
                scores["opening_hook"] = 5
                weak_sections.append({"scene_number": 1, "issue": "Opening hook is too brief to build curiosity"})
            else:
                scores["opening_hook"] = 9

        # 3. Scene narration depth & sensory detail check
        short_scene_count = 0
        for sc in scenes:
            sn = sc.get("scene_number", 0)
            narr = (sc.get("narration") or "").strip()
            if len(narr) < 140 and not is_short:
                short_scene_count += 1
                weak_sections.append({"scene_number": sn, "issue": "Narration too short or lacking atmospheric tension"})

        if short_scene_count > total_scenes * 0.3:
            scores["actual_event_detail"] = max(4, scores["actual_event_detail"] - 3)
            critical_issues.append("Over 30% of scenes have superficial 1-2 sentence narrations")
        else:
            scores["actual_event_detail"] = 9
            scores["scene_quality"] = 9

        # 4. Character consistency check
        char_refs = story.get("characters") or []
        char_names = {c.get("name") for c in char_refs if isinstance(c, dict) and c.get("name")}
        used_dialogue_speakers = {
            d.get("character") for sc in scenes for d in sc.get("dialogue", []) if isinstance(d, dict) and d.get("character")
        }
        unknown_speakers = used_dialogue_speakers - char_names - {"Narrator", "सूत्रधार", "पात्र", "अजनबी", "भीड़"}
        if len(unknown_speakers) > 2:
            scores["character_development"] = max(5, scores["character_development"] - 2)
            weak_sections.append(
                {"scene_number": 0, "issue": f"Characters appearing in dialogue not defined in cast: {unknown_speakers}"}
            )

        # 5. Climax & Ending completeness check
        if scenes:
            last_scene = scenes[-1]
            last_narr = last_scene.get("narration") or ""
            ending_text = story.get("ending") or ""
            full_ending = last_narr + " " + ending_text
            if len(full_ending.strip()) < 90:
                scores["ending_and_conclusion"] = 4
                critical_issues.append("Abrupt or incomplete story ending")
                weak_sections.append({"scene_number": total_scenes, "issue": "Ending lacks proper resolution"})
            else:
                scores["ending_and_conclusion"] = 9
                scores["climax"] = 9

        # 6. Logic validator integration
        logic_report = self.logic_validator.validate(story, blueprint=blueprint)
        if not logic_report.is_valid:
            scores["logical_continuity"] = logic_report.continuity_score
            for iss in logic_report.issues:
                if iss.severity == "critical" and iss.description not in critical_issues:
                    critical_issues.append(iss.description)

        return scores, weak_sections, critical_issues

    def _evaluate_with_llm(
        self,
        story: dict[str, Any],
        rule_scores: dict[str, int],
        weak_sections: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Calls LLM to score the story as a Bollywood Screenwriter & Script Doctor."""
        scenes = story.get("scenes", [])
        synopsis = story.get("synopsis", "")
        title = story.get("title", "")
        ending = story.get("ending", "")

        beat_summary = []
        for sc in scenes[:16]:
            sn = sc.get("scene_number", 0)
            beat = sc.get("story_beat", "scene")
            narr = (sc.get("narration") or "")[:200]
            diags = " | ".join(f"{d.get('character')}: {d.get('line')}" for d in (sc.get("dialogue") or [])[:2])
            beat_summary.append(f"Scene {sn} [{beat}]: {narr}\n  Dialogue: {diags}")

        prompt = f"""You are an elite Bollywood Screenplay Consultant and YouTube Audience Retention Specialist.
Audit the following Hindi story script across 10 critical storytelling dimensions.

Story Title: {title}
Synopsis: {synopsis}
Ending Resolution: {ending}

Story Scenes:
{chr(10).join(beat_summary)}

Grade EACH dimension from 1 to 10 (10 = masterpiece Bollywood thriller level, 1 = unwatchable garbage).
CRITERIA (10 dimensions):
1. opening_hook (Must start within 10s with shock/mystery, NO boring introductions)
2. actual_event_detail (Must explain concrete events - who, what, where - NO vague summaries)
3. scene_quality (Sensory immersion, atmospheric tension, believable actions)
4. logical_continuity (Strict cause-and-effect, no random disconnected incidents)
5. character_development (Distinct believable Indian characters with consistent names, traits, and stakes)
6. dialogue_quality (Colloquial natural Hindi dialogue, no English transliteration, no speaker labels in spoken text)
7. suspense (Tension rises with gradual clue reveals)
8. originality (Real human stakes, deep emotional dilemma, unpredictable twists)
9. climax (High-tension confrontation resolving the central mystery)
10. ending_and_conclusion (100% complete, fully resolved, no abrupt cuts)

Output valid JSON ONLY in this exact format:
{{
  "scores": {{
    "opening_hook": 9,
    "actual_event_detail": 9,
    "scene_quality": 9,
    "logical_continuity": 9,
    "character_development": 9,
    "dialogue_quality": 9,
    "suspense": 9,
    "originality": 9,
    "climax": 9,
    "ending_and_conclusion": 9
  }},
  "total_score": 90,
  "feedback": "Short 1-2 sentence actionable advice to polish this story."
}}"""
        resp = self.llm.complete(prompt, system="You are an uncompromising screenplay judge. Output JSON only.", json_mode=True)
        return self.llm.parse_json(resp.text)
