from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class PerformanceAnalyzer:
    """Aggregates snapshot metrics; defers low-sample conclusions."""

    @staticmethod
    def summarize(snapshots: list[dict[str, Any]]) -> dict[str, Any]:
        if not snapshots:
            return {"status": "no_data", "message": "No analytics snapshots yet."}

        latest = snapshots[-1].get("metrics", {})
        views = latest.get("views", 0)
        impressions = latest.get("impressions", 0)
        ctr = latest.get("impressions_ctr", 0.0)
        avg_view = latest.get("average_view_duration", 0.0)

        confidence = "low"
        if views >= 100 or impressions >= 500:
            confidence = "medium"
        if views >= 1000:
            confidence = "high"

        return {
            "views": views,
            "impressions": impressions,
            "ctr": ctr,
            "average_view_duration": avg_view,
            "confidence": confidence,
            "raw_latest": latest,
        }
