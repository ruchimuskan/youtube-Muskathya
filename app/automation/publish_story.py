from __future__ import annotations

import json
import logging
from pathlib import Path

from app.ai.seo_generator import SEOGenerator
from app.automation.output_manager import OutputManager
from app.config import get_settings
from app.creative.creative_package import CreativePackageWriter
from app.creative.thumbnail_engine import ThumbnailEngine
from app.database import Repository, session_scope
from app.database.models import StoryProject
from app.video.quality_checker import QualityChecker
from app.video.video_editor import VideoEditor
from app.youtube.upload_dispatch import dispatch_youtube_upload

logger = logging.getLogger(__name__)


def publish_story(
    story_id: int,
    *,
    upload: bool = True,
    privacy: str | None = None,
) -> dict:
    settings = get_settings()
    work_dir = settings.output_dir / f"story_{story_id:03d}"
    video_path = work_dir / "final" / "final_video.mp4"
    if not video_path.exists():
        video_path = work_dir / "final.mp4"
    if not video_path.exists():
        raise FileNotFoundError(f"No final video for story_{story_id:03d}")

    with session_scope() as session:
        story_row = session.get(StoryProject, story_id)
        if not story_row:
            raise ValueError(f"Story id {story_id} not found")
        story = dict(story_row.story_json or {})
        story_language = story_row.language
        story.setdefault("title", story_row.title)
        story.setdefault("story_project_id", story_id)
        story.setdefault("target_duration_sec", story_row.target_duration_sec)
        story.setdefault("language", story_row.language)
        default_category = story_row.genre

    OutputManager(work_dir).save_full_story_json(story)

    category_id = story.get("content_category_id", default_category)
    thumb_dir = work_dir / "thumbnail"
    thumb_dir.mkdir(parents=True, exist_ok=True)
    images = sorted((work_dir / "images").glob("scene_*.png"))
    if not images:
        raise FileNotFoundError("Missing scene images")

    thumb_engine = ThumbnailEngine()
    _, thumb_concepts, best_thumb = thumb_engine.generate(
        story, category_id, images[0], thumb_dir, count=3, all_scene_images=images
    )

    seo_gen = SEOGenerator()
    seo = seo_gen.generate_full_package(
        story,
        story_language,
        category_id=category_id,
        topic_research=story.get("research", {}),
        thumbnail_text=thumb_concepts[0].get("hindi_text") if thumb_concepts else None,
    )

    probe = VideoEditor().probe(video_path)
    duration = float(probe.get("format", {}).get("duration", 0))
    qc = QualityChecker().inspect_video(
        video_path,
        expected_aspect="16:9",
        min_duration=60,
        max_duration=1200,
        thumbnail_path=best_thumb,
        title=seo["recommended_title"],
        story_complete=bool(story.get("ending")),
        language=story_language,
    )

    package = {
        "title_candidates": seo.get("title_variations"),
        "selected_title": seo.get("recommended_title"),
        "description": seo.get("description"),
        "thumbnail_final_path": str(best_thumb),
        "thumbnail_concepts": thumb_concepts,
        "seo_report": seo.get("seo_report"),
    }
    CreativePackageWriter(work_dir).save_all(package)

    with session_scope() as session:
        repo = Repository(session)
        asset = repo.create_video_asset(
            story_id=story_id,
            local_path=str(video_path),
            thumbnail_path=str(best_thumb),
            aspect_ratio="16:9",
            qc_passed=qc.passed,
            qc_report=qc.to_dict(),
        )
        asset_id = asset.id

    result = {
        "story_id": story_id,
        "video_path": str(video_path),
        "thumbnail_path": str(best_thumb),
        "title": seo["recommended_title"],
        "duration_sec": duration,
        "qc_passed": qc.passed,
        "video_asset_id": asset_id,
    }

    if upload:
        if not qc.passed:
            raise RuntimeError(f"QC failed: {qc.critical_failures}")
        upload_info = dispatch_youtube_upload(
            video_asset_id=asset_id,
            video_path=video_path,
            thumbnail_path=best_thumb,
            metadata={
                "title": seo["recommended_title"],
                "description": seo.get("description", ""),
                "tags": seo.get("tags", []),
                "category_id": seo.get("category_id", "24"),
            },
            story_id=story_id,
        )
        result["upload_status"] = upload_info.get("status")
        result["scheduled_publish_at"] = upload_info.get("publish_at")
        if upload_info.get("status") != "queued":
            result["youtube_url"] = upload_info.get("youtube_url")
            result["youtube_video_id"] = upload_info.get("youtube_video_id")
            result["thumbnail_status"] = upload_info.get("thumbnail_status")

    meta_path = work_dir / "youtube_metadata.json"
    meta_path.write_text(json.dumps(seo, ensure_ascii=False, indent=2), encoding="utf-8")
    return result
