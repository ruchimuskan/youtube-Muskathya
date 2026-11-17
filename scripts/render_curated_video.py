from __future__ import annotations

import json
import logging
import shutil
import sys
from pathlib import Path

# Add project root to sys.path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.automation.output_manager import OutputManager
from app.creative.creative_package import CreativePackageWriter
from app.creative.thumbnail_engine import ThumbnailEngine
from app.database import Repository, session_scope
from app.images.image_generator import ImageGenerator
from app.video.video_editor import VideoEditor
from app.voice.dialogue_manager import DialogueManager
from app.voice.voice_director import VoiceDirector
from app.ai.seo_generator import SEOGenerator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("render_curated")


def render_story_dict(story: dict) -> Path:
    settings = get_settings()
    
    # Save in DB to get a story_project_id
    with session_scope() as session:
        repo = Repository(session)
        row = repo.create_story(
            title=story.get("title", "Untitled"),
            language="hi",
            genre="suspense",
            target_duration_sec=story.get("target_duration_sec", 300),
            is_short=False,
            story_json=story,
            lessons_applied={"source": "master_screenplay_curated"},
        )
        story_id = row.id

    story["story_project_id"] = story_id
    work_dir = settings.output_dir / f"story_{story_id:03d}"
    output_mgr = OutputManager(work_dir)
    output_mgr.dirs["audio"].mkdir(parents=True, exist_ok=True)
    output_mgr.dirs["images"].mkdir(parents=True, exist_ok=True)
    output_mgr.dirs["final"].mkdir(parents=True, exist_ok=True)
    output_mgr.dirs["thumbnail"].mkdir(parents=True, exist_ok=True)

    # Save initial story.json
    (work_dir / "story.json").write_text(json.dumps(story, ensure_ascii=False, indent=2), encoding="utf-8")

    logger.info("Step 1/5: Generating high-quality scene images...")
    images_gen = ImageGenerator()
    image_paths, _ = images_gen.generate_scene_images(story, output_mgr.dirs["images"], "16:9")
    logger.info("Images ready: %d scene images", len(image_paths))

    logger.info("Step 2/5: Synthesizing natural Hindi voice-over with Piper TTS...")
    voice_director = VoiceDirector()
    vp = voice_director.plan("suspense_thriller", story)
    story["voice_plan"] = vp.to_dict()

    voice = DialogueManager()
    audio_segments = voice.render_story_audio(story, output_mgr.dirs["audio"], "hi")
    logger.info("Audio ready: %d segments synthesized", len(audio_segments))

    logger.info("Step 3/5: Rendering 1080p Full HD video with motion, subtitles and suspense BGM...")
    video_editor = VideoEditor()
    final_path = output_mgr.dirs["final"] / "final_video.mp4"
    video_editor.render(
        story,
        image_paths,
        audio_segments,
        work_dir,
        final_path,
        aspect_ratio="16:9",
    )
    shutil.copy(final_path, work_dir / "final.mp4")
    logger.info("Video successfully rendered at %s", final_path)

    logger.info("Step 4/5: Generating high-CTR thumbnails...")
    thumb_engine = ThumbnailEngine()
    thumb_variants, thumb_concepts, best_thumb = thumb_engine.generate(
        story,
        "suspense_thriller",
        image_paths[0],
        output_mgr.dirs["thumbnail"],
        count=3,
        all_scene_images=image_paths,
    )
    logger.info("Thumbnail ready: %s", best_thumb)

    logger.info("Step 5/5: Generating SEO metadata package...")
    seo_gen = SEOGenerator()
    try:
        seo = seo_gen.generate(story, "hi")
        (work_dir / "youtube_metadata.json").write_text(json.dumps(seo, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:
        logger.warning("SEO generation skipped: %s", exc)

    logger.info("ALL DONE! Story %d is ready at %s", story_id, final_path)
    return final_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python render_curated_video.py <path_to_story_json>")
        sys.exit(1)
    
    story_file = Path(sys.argv[1])
    story_data = json.loads(story_file.read_text(encoding="utf-8"))
    render_story_dict(story_data)
