from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from googleapiclient.discovery import build

from app.database import session_scope
from app.database.models import VideoPerformanceSnapshot
from app.youtube.oauth import YouTubeOAuth

logger = logging.getLogger(__name__)


class YouTubeAnalytics:
    def __init__(self, oauth: YouTubeOAuth | None = None) -> None:
        self.oauth = oauth or YouTubeOAuth()

    def _analytics(self):
        creds = self.oauth.load_credentials()
        if not creds:
            raise RuntimeError("YouTube OAuth required")
        return build("youtubeAnalytics", "v2", credentials=creds)

    def fetch_video_metrics(self, video_id: str, snapshot_label: str) -> dict[str, Any]:
        analytics = self._analytics()
        end = date.today()
        start = end - timedelta(days=28)
        resp = (
            analytics.reports()
            .query(
                ids="channel==MINE",
                startDate=start.isoformat(),
                endDate=end.isoformat(),
                metrics="views,estimatedMinutesWatched,averageViewDuration,likes,comments,shares",
                dimensions="video",
                filters=f"video=={video_id}",
            )
            .execute()
        )
        rows = resp.get("rows", [])
        metrics: dict[str, Any] = {"views": 0, "snapshot_label": snapshot_label}
        if rows:
            # views, minutes, avg duration, likes, comments, shares
            row = rows[0]
            metrics.update(
                {
                    "views": row[1],
                    "estimated_minutes_watched": row[2],
                    "average_view_duration": row[3],
                    "likes": row[4],
                    "comments": row[5],
                    "shares": row[6] if len(row) > 6 else 0,
                }
            )
        return metrics

    def save_snapshot(self, video_asset_id: int, snapshot_label: str, video_id: str) -> None:
        metrics = self.fetch_video_metrics(video_id, snapshot_label)
        with session_scope() as session:
            session.add(
                VideoPerformanceSnapshot(
                    video_asset_id=video_asset_id,
                    snapshot_label=snapshot_label,
                    metrics=metrics,
                )
            )
