from __future__ import annotations

import logging
from typing import Any

from app.ai.providers import LLMRouter
from app.database import Repository, session_scope
from app.database.models import MistakeReport, ProductionQualityCheck

logger = logging.getLogger(__name__)


class LearningEngine:
    def __init__(self, llm: LLMRouter | None = None) -> None:
        self.llm = llm or LLMRouter()

    def analyze_video(
        self,
        story: dict[str, Any],
        qc_report: dict[str, Any],
        performance: dict[str, Any],
    ) -> dict[str, Any]:
        prompt = f"""Analyze this YouTube video's production and performance.
Do not assume low views mean bad content — consider impressions, CTR, age, sample size.

Story synopsis: {story.get("synopsis")}
QC report: {qc_report}
Performance summary: {performance}

Return JSON:
{{
  "what_worked": ["..."],
  "what_failed": ["..."],
  "underperformance_reasons": ["..."],
  "issue_category": "content|packaging|search|distribution|insufficient_data",
  "evidence": ["..."],
  "recommendations": ["..."],
  "apply_next_video": ["..."]
}}"""

        response = self.llm.complete(prompt, system="Output JSON only.", json_mode=True)
        return self.llm.parse_json(response.text)

    def persist_report(self, video_asset_id: int, report: dict[str, Any]) -> None:
        with session_scope() as session:
            repo = Repository(session)
            session.add(MistakeReport(video_asset_id=video_asset_id, report_json=report))
            for item in report.get("apply_next_video", []):
                repo.add_lesson(category=report.get("issue_category", "general"), lesson=item)
            repo.audit("learning_report_saved", "video_asset", str(video_asset_id))

    def record_qc(self, video_asset_id: int, check_type: str, passed: bool, details: dict) -> None:
        with session_scope() as session:
            session.add(
                ProductionQualityCheck(
                    video_asset_id=video_asset_id,
                    check_type=check_type,
                    passed=passed,
                    details=details,
                )
            )
