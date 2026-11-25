from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from typing import Any

from app.ai.providers import LLMRouter
from app.ai.repetition_detector import RepetitionDetector
from app.ai.story_logic_validator import StoryLogicValidator
from app.ai.vague_sentence_detector import VagueSentenceDetector

logger = logging.getLogger(__name__)


@dataclass
class StoryAuditReport:
    passed: bool
    total_score: int
    base_score: int
    repetition_penalty: int
    vague_penalty: int
    minimum_required: int = 85
    dimensions: dict[str, int] = field(default_factory=dict)
    weak_sections: list[dict[str, Any]] = field(default_factory=list)
    critical_issues: list[str] = field(default_factory=list)
    feedback_for_rewrite: str = ""
    evaluation_method: str = "hybrid_auditor"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class StoryQualityAuditor:
    """
    Independent Bollywood Screenplay Quality Auditor.
    Evaluates 10 core storytelling parameters from 0 to 10,
    enforcing a strict 85/100 minimum bar with explicit repetition
    and vague-storytelling penalties.
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

    def __init__(self, llm: LLMRouter | None = None) -> None:
        self.llm = llm or LLMRouter()
        self.repetition_detector = RepetitionDetector()
        self.vague_detector = VagueSentenceDetector()
        self.logic_validator = StoryLogicValidator()

    def audit(
        self, story: dict[str, Any], blueprint: dict[str, Any] | None = None
    ) -> StoryAuditReport:
        """
        Runs comprehensive programmatic analysis plus LLM evaluation.
        Deducts severe penalties for repetition, vague storytelling, or logical gaps.
        """
        scenes = story.get("scenes") or []
        if not scenes:
            return StoryAuditReport(
                passed=False,
                total_score=0,
                base_score=0,
                repetition_penalty=0,
                vague_penalty=0,
                critical_issues=["Story contains zero scenes."],
                feedback_for_rewrite="Generate a complete scene-based story.",
            )

        # 1. Programmatic Repetition Audit
        rep_penalty, rep_critiques = self.repetition_detector.calculate_repetition_penalty(story)

        # 2. Programmatic Vague Sentence Audit
        vague_penalty, vague_critiques = self.vague_detector.calculate_vague_penalty(story)

        # 3. Logic & Continuity Audit
        logic_report = self.logic_validator.validate(story, blueprint=blueprint)

        # 4. Programmatic Dimension Baseline
        dim_scores, weak_sections, programmatic_criticals = self._rule_dimension_scores(
            story, rep_penalty, vague_penalty, logic_report
        )

        all_critical_issues = list(programmatic_criticals)
        if logic_report.critical_count > 0:
            for iss in logic_report.issues:
                if iss.severity == "critical":
                    all_critical_issues.append(f"Logic Flaw: {iss.description}")

        # 5. LLM Semantic Screenplay Evaluation
        llm_dim_scores: dict[str, int] = {}
        llm_feedback = ""
        eval_method = "hybrid_auditor"

        try:
            llm_res = self._evaluate_with_llm(story, dim_scores, weak_sections)
            llm_dim_scores = llm_res.get("scores", {})
            llm_feedback = llm_res.get("feedback", "")
            eval_method = "llm_validated_auditor"
        except Exception as exc:
            logger.warning("LLM script auditor evaluation skipped (%s); using deterministic auditor", exc)
            eval_method = "deterministic_auditor"

        # Combine dimension scores (70% LLM, 30% programmatic if LLM succeeded)
        final_dimensions: dict[str, int] = {}
        base_sum = 0
        for dim in self.DIMENSION_KEYS:
            rule_val = dim_scores.get(dim, 7)
            if dim in llm_dim_scores:
                comb = int(round(llm_dim_scores[dim] * 0.7 + rule_val * 0.3))
            else:
                comb = rule_val
            comb = max(0, min(10, comb))
            final_dimensions[dim] = comb
            base_sum += comb

        # Calculate final penalized score
        # Total score = Base sum (0-100) - Repetition penalty - Vague penalty
        penalized_score = max(0, min(100, base_sum - rep_penalty - vague_penalty))

        # Add critical findings if penalties are too severe
        if rep_penalty > 0:
            all_critical_issues.extend(rep_critiques[:3])
        if vague_penalty > 0:
            all_critical_issues.extend(vague_critiques[:3])

        # Strict pass criteria
        passed = (
            penalized_score >= self.MIN_PASSING_SCORE
            and rep_penalty <= 2
            and vague_penalty <= 2
            and len(all_critical_issues) == 0
        )

        # Assemble actionable feedback
        feedback_parts: list[str] = []
        if all_critical_issues:
            feedback_parts.append("CRITICAL FLAWS:\n- " + "\n- ".join(all_critical_issues))
        if weak_sections:
            feedback_parts.append(
                "WEAK SCENES TO REWRITE:\n- "
                + "\n- ".join(f"Scene {w.get('scene_number')}: {w.get('issue')}" for w in weak_sections[:5])
            )
        if rep_critiques:
            feedback_parts.append("REPETITION FLAWS:\n- " + "\n- ".join(rep_critiques[:3]))
        if vague_critiques:
            feedback_parts.append("VAGUE TELLING-NOT-SHOWING FLAWS:\n- " + "\n- ".join(vague_critiques[:3]))
        if llm_feedback:
            feedback_parts.append(f"SCREENPLAY DOCTOR NOTE: {llm_feedback}")

        return StoryAuditReport(
            passed=passed,
            total_score=penalized_score,
            base_score=base_sum,
            repetition_penalty=rep_penalty,
            vague_penalty=vague_penalty,
            minimum_required=self.MIN_PASSING_SCORE,
            dimensions=final_dimensions,
            weak_sections=weak_sections,
            critical_issues=all_critical_issues,
            feedback_for_rewrite="\n\n".join(feedback_parts),
            evaluation_method=eval_method,
        )

    def _rule_dimension_scores(
        self,
        story: dict[str, Any],
        rep_penalty: int,
        vague_penalty: int,
        logic_report: Any,
    ) -> tuple[dict[str, int], list[dict[str, Any]], list[str]]:
        scenes = story.get("scenes") or []
        is_short = bool(story.get("is_short"))
        criticals: list[str] = []
        weaks: list[dict[str, Any]] = []

        scores: dict[str, int] = {k: 8 for k in self.DIMENSION_KEYS}

        # 1. Opening hook
        if scenes:
            s1 = scenes[0]
            s1_text = (s1.get("narration") or "") + " " + " ".join(d.get("line", "") for d in s1.get("dialogue", []))
            boring_starts = ["एक बार की बात", "एक गाँव में", "एक समय की बात", "किसी गाँव में"]
            if any(b in s1_text for b in boring_starts):
                scores["opening_hook"] = 3
                weaks.append({"scene_number": 1, "issue": "Generic fairytale intro; must begin with shocking incident"})
                criticals.append("Opening hook uses cliché fairytale beginning.")
            elif len(s1_text) < 140:
                scores["opening_hook"] = 5
                weaks.append({"scene_number": 1, "issue": "Opening hook is too brief to establish immediate stakes"})
            else:
                scores["opening_hook"] = 9

        # 2. Actual event detail & scene quality
        short_narr_count = 0
        dialogue_counts = 0
        for sc in scenes:
            sn = sc.get("scene_number", 0)
            narr = (sc.get("narration") or "").strip()
            if len(narr) < 150 and not is_short:
                short_narr_count += 1
                weaks.append({"scene_number": sn, "issue": "Scene narration lacks concrete sensory event details"})
            dialogues = sc.get("dialogue") or []
            dialogue_counts += len(dialogues)

        if short_narr_count > 0:
            scores["actual_event_detail"] = max(2, 9 - short_narr_count * 2)
            scores["scene_quality"] = max(3, 9 - short_narr_count)
            if short_narr_count > len(scenes) * 0.25:
                criticals.append(f"{short_narr_count} scenes have superficial 1-2 sentence narrations without events.")
        else:
            scores["actual_event_detail"] = 9
            scores["scene_quality"] = 9

        # 3. Dialogue quality
        avg_dialogue = dialogue_counts / max(1, len(scenes))
        if avg_dialogue < 1.0 and not is_short:
            scores["dialogue_quality"] = 4
            weaks.append({"scene_number": 0, "issue": "Low dialogue presence; scenes feel narrated rather than acted"})
        elif rep_penalty > 0:
            scores["dialogue_quality"] = max(3, 8 - rep_penalty // 2)
        else:
            scores["dialogue_quality"] = 9

        # 4. Logical continuity
        scores["logical_continuity"] = logic_report.continuity_score

        # 5. Suspense & Climax
        if len(scenes) >= 5:
            scores["suspense"] = 9
            scores["climax"] = 9
        else:
            scores["suspense"] = 5
            scores["climax"] = 5

        # 6. Ending and conclusion
        ending = (story.get("ending") or "").strip()
        moral = (story.get("conclusion_moral") or "").strip()
        if len(ending) < 90:
            scores["ending_and_conclusion"] = 4
            criticals.append("Ending is too brief or fails to show final consequences.")
            weaks.append({"scene_number": len(scenes), "issue": "Incomplete ending"})
        else:
            scores["ending_and_conclusion"] = 9

        return scores, weaks, criticals

    def _evaluate_with_llm(
        self,
        story: dict[str, Any],
        dim_scores: dict[str, int],
        weak_sections: list[dict[str, Any]],
    ) -> dict[str, Any]:
        scenes = story.get("scenes") or []
        synopsis = story.get("synopsis", "")
        title = story.get("title", "")
        ending = story.get("ending", "")

        beat_summary = []
        for sc in scenes[:16]:
            sn = sc.get("scene_number", 0)
            narr = (sc.get("narration") or "")[:220]
            diags = " | ".join(f"{d.get('character')}: {d.get('line')}" for d in (sc.get("dialogue") or [])[:2])
            beat_summary.append(f"Scene {sn}: {narr}\n  Dialogue: {diags}")

        prompt = f"""You are a senior Bollywood Screenwriter, Novelist, and Story Quality Auditor.
Audit this Hindi story script across 10 critical parameters.

Title: {title}
Synopsis: {synopsis}
Ending: {ending}

Scenes Outline:
{chr(10).join(beat_summary)}

Audit these 10 parameters (Score each 0 to 10):
1. opening_hook (Must start directly with shock/mystery, NO generic intro)
2. actual_event_detail (Must SHOW concrete events - who, where, what happened - NO vague summaries like 'उसे बहुत संघर्ष करना पड़ा')
3. scene_quality (Sensory immersion, atmospheric tension, believable actions)
4. logical_continuity (Cause-and-effect chain, setups & payoffs, no plot holes)
5. character_development (Clear motivations, grounded relationships, believable stakes)
6. dialogue_quality (Natural spoken Hindi, distinct personalities, advances plot, no filler questions)
7. suspense (Escalating complications, clues, curiosity beats)
8. originality (Unpredictable twists, authentic Indian context, no clichés)
9. climax (High-stakes confrontation resolving the mystery with evidence)
10. ending_and_conclusion (Complete resolution showing what happened to all characters, satisfying payoff)

Return JSON ONLY:
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
  "feedback": "Concise actionable note on story strengths and flaws."
}}"""

        resp = self.llm.complete(
            prompt,
            system="You are an uncompromising screenplay judge. Output JSON only.",
            json_mode=True,
        )
        return self.llm.parse_json(resp.text)
