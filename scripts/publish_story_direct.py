"""
Directly publish a rendered story video to YouTube using existing metadata and thumbnail.
Usage: .venv/bin/python scripts/publish_story_direct.py --story-id 14 --privacy public
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings
from app.creative.thumbnail_paths import canonical_thumbnail_path
from app.database import Repository, session_scope
from app.database.models import StoryProject, VideoAsset
from app.video.quality_checker import QualityChecker
from app.video.video_editor import VideoEditor
from app.youtube.uploader import YouTubeUploader

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def publish_direct(
    story_id: int,
    video_path_arg: str | None = None,
    privacy: str = "public",
    force: bool = True,
) -> dict:
    settings = get_settings()
    work_dir = settings.output_dir / f"story_{story_id:03d}"
    if not work_dir.exists():
        raise FileNotFoundError(f"Story folder not found: {work_dir}")

    if video_path_arg:
        video_path = Path(video_path_arg).resolve()
    else:
        video_path = work_dir / "final" / "final_video.mp4"
        if not video_path.exists():
            video_path = work_dir / "final.mp4"

    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found at {video_path}")

    # Load metadata
    meta_path = work_dir / "youtube_metadata.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"youtube_metadata.json not found in {work_dir}")
    raw_meta = json.loads(meta_path.read_text(encoding="utf-8"))

    title = (
        raw_meta.get("recommended_title")
        or raw_meta.get("title")
        or raw_meta.get("main_topic")
        or f"Story {story_id}"
    )
    description = raw_meta.get("description", "")
    tags = raw_meta.get("tags", [])
    category_id = str(raw_meta.get("category_id", "24"))

    upload_metadata = {
        "title": title,
        "description": description,
        "tags": tags,
        "category_id": category_id,
    }

    # Thumbnail
    thumb_path = canonical_thumbnail_path(story_id)
    if not thumb_path.exists():
        alt_thumb = work_dir / "thumbnail" / "story_014_thumbnail.jpg"
        if alt_thumb.exists():
            thumb_path = alt_thumb
        else:
            candidates = sorted((work_dir / "thumbnail").glob("*.jpg"))
            if candidates:
                thumb_path = candidates[0]
            else:
                thumb_path = None

    logger.info("Publishing video: %s (size: %.1f MB)", video_path, video_path.stat().st_size / 1e6)
    logger.info("Using thumbnail: %s", thumb_path)
    logger.info("Title: %s", title)

    # Video probe & QC
    editor = VideoEditor()
    probe = editor.probe(video_path)
    duration = float(probe.get("format", {}).get("duration", 0))

    qc = QualityChecker().inspect_video(
        video_path,
        expected_aspect="16:9",
        min_duration=30,
        max_duration=1800,
        thumbnail_path=thumb_path,
        title=title,
        story_complete=True,
        language="hi",
    )
    if not qc.passed:
        logger.warning("QC warnings/failures: %s", qc.critical_failures)

    # Create VideoAsset in DB
    with session_scope() as session:
        repo = Repository(session)
        asset = repo.create_video_asset(
            story_id=story_id,
            local_path=str(video_path.relative_to(settings.output_dir.parent) if video_path.is_relative_to(settings.output_dir.parent) else video_path),
            thumbnail_path=str(thumb_path) if thumb_path else None,
            aspect_ratio="16:9",
            duration_sec=duration,
            qc_passed=qc.passed,
            qc_report=qc.to_dict(),
        )
        asset_id = asset.id

    logger.info("Created VideoAsset ID: %d", asset_id)

    # Upload to YouTube
    uploader = YouTubeUploader()
    upload_result = uploader.upload_video(
        video_asset_id=asset_id,
        file_path=video_path,
        metadata=upload_metadata,
        privacy=privacy,
        publish_at=None,
        thumbnail_path=thumb_path,
        force=force,
    )

    logger.info("Upload successful! YouTube Video ID: %s", upload_result.get("youtube_video_id"))
    logger.info("YouTube URL: %s", upload_result.get("youtube_url"))
    return upload_result


def main() -> None:
    parser = argparse.ArgumentParser(description="Direct YouTube Story Publisher")
    parser.add_argument("--story-id", type=int, required=True, help="Story ID to publish")
    parser.add_argument("--video-path", type=str, default=None, help="Explicit video file path")
    parser.add_argument("--privacy", type=str, default="public", choices=["public", "unlisted", "private"])
    parser.add_argument("--force", action="store_true", default=True, help="Bypass daily upload limit")
    args = parser.parse_args()

    result = publish_direct(
        story_id=args.story_id,
        video_path_arg=args.video_path,
        privacy=args.privacy,
        force=args.force,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
