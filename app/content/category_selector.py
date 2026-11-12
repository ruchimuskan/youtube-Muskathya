from __future__ import annotations

import logging
import random
from collections import Counter
from dataclasses import dataclass
from typing import Any

from app.ai.providers import LLMRouter
from app.content.categories import CATEGORIES, get_category
from app.content.category_config import load_category_config
from app.database import Repository, session_scope
from sqlalchemy import desc, select
from app.database.models import StoryProject, VideoPerformanceSnapshot

logger = logging.getLogger(__name__)


@dataclass
class CategorySelection:
    category_id: str
    category_name_hi: str
    legacy_genre: str
    format_mode: str
    target_duration_sec: int
    is_short: bool
    min_scenes: int
    max_scenes: int
    visual_style: str
    selection_reason: str
    topic_research: dict[str, Any]


class CategorySelector:
    def __init__(self, llm: LLMRouter | None = None) -> None:
        self.llm = llm or LLMRouter()
        self.config = load_category_config()

    def _recent_category_counts(self, limit: int = 12) -> Counter[str]:
        counts: Counter[str] = Counter()
        with session_scope() as session:
            rows = list(
                session.scalars(select(StoryProject).order_by(desc(StoryProject.created_at)).limit(limit))
            )
            for row in rows:
                sj = row.story_json or {}
                cid = sj.get("content_category_id") or row.genre
                counts[cid] += 1
        return counts

    def _performance_by_genre(self) -> dict[str, float]:
        """Lightweight: average views per category when analytics snapshots exist."""
        scores: dict[str, list[float]] = {}
        try:
            with session_scope() as session:
                stories = {
                    s.id: (s.story_json or {}).get("content_category_id", s.genre)
                    for s in session.scalars(select(StoryProject)).all()
                }
                from app.database.models import VideoAsset

                for snap in session.scalars(select(VideoPerformanceSnapshot)).all():
                    asset = session.get(VideoAsset, snap.video_asset_id)
                    if not asset or not asset.story_id:
                        continue
                    cid = stories.get(asset.story_id, "moral")
                    views = float((snap.metrics or {}).get("views", 0))
                    scores.setdefault(cid, []).append(views)
        except Exception as exc:
            logger.debug("Performance by genre skipped: %s", exc)
        return {k: (sum(v) / len(v) if v else 0) for k, v in scores.items()}

    def _weighted_choice(self, enabled: list[str], weights: dict[str, float]) -> str:
        recent = self._recent_category_counts()
        perf = self._performance_by_genre()
        adjusted: dict[str, float] = {}
        for cid in enabled:
            base = weights.get(cid, get_category(cid).default_weight)
            penalty = 0.85 ** recent.get(cid, 0)
            boost = 1.0 + min(perf.get(cid, 0) / 10_000.0, 0.25)
            adjusted[cid] = max(base * penalty * boost, 0.01)
        ids = list(adjusted.keys())
        probs = [adjusted[i] for i in ids]
        return random.choices(ids, weights=probs, k=1)[0]

    def _resolve_format(self) -> tuple[str, int, int, bool, int, int]:
        from app.content.categories import format_duration_range
        from app.config import get_settings

        settings = get_settings()
        mode = self.config.get("video_format_mode", "long")
        if settings.shorts_ratio > 0 and random.random() < settings.shorts_ratio:
            mode = "short"
        if mode == "auto":
            mode = random.choices(["long", "extended", "short"], weights=[0.7, 0.2, 0.1], k=1)[0]
        lo, hi, min_sc, max_sc = format_duration_range(mode)
        if mode == "short":
            return mode, random.randint(lo, hi), 1, True, min_sc, max_sc
        target = random.randint(
            max(lo, settings.video_min_duration_sec if mode == "long" else lo),
            min(hi, settings.video_max_duration_sec if mode == "long" else hi),
        )
        return mode, target, 1, False, min_sc, max_sc

    def select(self, *, topic_hint: str | None = None) -> CategorySelection:
        manual = self.config.get("manual_category_id")
        enabled = [c for c in (self.config.get("enabled_categories") or []) if c in CATEGORIES]
        if not enabled:
            enabled = ["moral"]

        weights = self.config.get("category_weights") or {}
        if manual and manual in enabled:
            category_id = manual
            reason = f"Manual category selected in dashboard config: {manual}"
        elif self.config.get("auto_category_selection", True):
            category_id = self._weighted_choice(enabled, weights)
            recent = dict(self._recent_category_counts())
            reason = (
                f"Auto-selected {category_id} using distribution weights, "
                f"recent mix {recent}, avoiding over-repeat."
            )
        else:
            category_id = enabled[0]
            reason = "Auto selection off; using first enabled category."

        category = get_category(category_id)
        fmt_mode, duration, aspect_dummy, is_short, min_sc, max_sc = self._resolve_format()
        visual = self.config.get("visual_style_override") or category.visual_style

        topic = self._research_topic(category_id, category.legacy_genre, is_short, topic_hint)
        reason += f" Topic: {topic.get('main_topic', '')}. Intent: {topic.get('search_intent', '')}"

        with session_scope() as session:
            Repository(session).audit(
                "category_selected",
                "content",
                category_id,
                {"reason": reason, "topic": topic},
            )

        return CategorySelection(
            category_id=category_id,
            category_name_hi=category.name_hi,
            legacy_genre=category.legacy_genre,
            format_mode=fmt_mode,
            target_duration_sec=duration,
            is_short=is_short,
            min_scenes=min_sc,
            max_scenes=max_sc,
            visual_style=visual,
            selection_reason=reason,
            topic_research=topic,
        )

    def _research_topic(
        self, category_id: str, genre: str, is_short: bool, topic_hint: str | None = None
    ) -> dict[str, Any]:
        recent_topics: list[str] = []
        with session_scope() as session:
            for row in session.scalars(
                select(StoryProject).order_by(desc(StoryProject.created_at)).limit(15)
            ):
                sj = row.story_json or {}
                t = sj.get("title") or row.title
                if t:
                    recent_topics.append(str(t))

        lessons: list[str] = []
        with session_scope() as session:
            for row in Repository(session).get_recent_lessons(10):
                lessons.append(f"[{row.category}] {row.lesson}")

        prompt = f"""You are a Hindi YouTube story strategist.
Category: {category_id} ({get_category(category_id).name_hi})
Genre: {genre}
Format: {"Short 30-60s" if is_short else "Long-form Hindi story video"}

Channel lessons:
{chr(10).join(lessons) if lessons else "None yet"}

Avoid repeating these recent titles:
{", ".join(recent_topics[:10]) if recent_topics else "none"}

User topic hint (must follow if set): {topic_hint or "none"}

Pick ONE original topic with measurable search interest in Hindi audience.
Theme should match category {category_id} and hint when provided.
JSON only:
{{
  "main_topic": "Hindi topic title",
  "audience_hook": "...",
  "search_intent": "...",
  "suggested_keywords": ["..."],
  "competition_note": "...",
  "uniqueness_note": "...",
  "content_gap": "..."
}}"""
        response = self.llm.complete(
            prompt,
            system="Original ideas only. Valid JSON.",
            json_mode=True,
        )
        return self.llm.parse_json(response.text)
