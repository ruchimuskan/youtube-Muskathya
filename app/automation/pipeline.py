from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any

from app.ai.seo_generator import SEOGenerator
from app.ai.story_generator import StoryGenerationRequest, StoryGenerator
from app.automation.job_manager import JobManager
from app.automation.notifications import Notifier
from app.automation.output_manager import OutputManager
from app.config import get_settings
from app.content.calendar import ContentCalendar
from app.content.category_selector import CategorySelector
from app.creative.creative_package import CreativePackageWriter
from app.creative.thumbnail_engine import ThumbnailEngine
from app.database import Repository, session_scope
from app.images.image_generator import ImageGenerator
from app.video.audio_director import AudioDirector
from app.video.quality_checker import QualityChecker
from app.video.video_editor import VideoEditor
from app.voice.dialogue_manager import DialogueManager
from app.voice.voice_director import VoiceDirector
from app.youtube.scheduler import PublishScheduler
from app.youtube.uploader import YouTubeUploader

logger = logging.getLogger(__name__)


class ContentPipeline:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.jobs = JobManager()
        self.notify = Notifier()
        self.story_gen = StoryGenerator()
        self.seo_gen = SEOGenerator()
        self.images = ImageGenerator()
        self.voice = DialogueManager()
        self.video = VideoEditor()
        self.qc = QualityChecker()
        self.thumb_engine = ThumbnailEngine()
        self.uploader = YouTubeUploader()
        self.scheduler = PublishScheduler()
        self.category_selector = CategorySelector()
        self.voice_director = VoiceDirector()
        self.audio_director = AudioDirector()
        self.calendar = ContentCalendar()

    def run(
        self,
        *,
        upload: bool = False,
        idempotency_key: str | None = None,
        category_id: str | None = None,
        topic_hint: str | None = None,
    ) -> dict[str, Any]:
        if self.settings.emergency_stop:
            raise RuntimeError("Emergency stop enabled")

        job_id = self.jobs.start("generate_youtube_video", idempotency_key)
        result: dict[str, Any] = {"steps": []}

        try:
            selection = self.category_selector.select(topic_hint=topic_hint)
            if category_id:
                from app.content.categories import get_category

                cat = get_category(category_id)
                selection.category_id = category_id
                selection.legacy_genre = cat.legacy_genre
                selection.category_name_hi = cat.name_hi
                selection.selection_reason = f"CLI override: {category_id}"

            target = selection.target_duration_sec
            is_short = selection.is_short
            aspect = "9:16" if is_short else self.settings.video_aspect_ratio
            result["category"] = {
                "id": selection.category_id,
                "name_hi": selection.category_name_hi,
                "reason": selection.selection_reason,
                "format_mode": selection.format_mode,
            }
            result["target_duration_sec"] = target
            result["is_short"] = is_short
            result["steps"].append("category_selected")

            self.calendar.plan_entry(
                category_id=selection.category_id,
                topic=selection.topic_research.get("main_topic", ""),
                format_mode=selection.format_mode,
                status="generating",
            )

            voice_plan = self.voice_director.plan(selection.category_id, {"suspense_level": 5})
            story: dict[str, Any] | None = None

            req = StoryGenerationRequest(
                language=self.settings.default_language,
                genre=selection.legacy_genre,
                target_duration_sec=target,
                is_short=is_short,
                category_id=selection.category_id,
                topic_research=selection.topic_research,
                min_scenes=selection.min_scenes,
                max_scenes=selection.max_scenes,
                visual_style=selection.visual_style,
                content_style=f"cinematic Hindi {selection.category_name_hi}",
            )
            story = self.story_gen.generate(req)
            story["voice_plan"] = voice_plan.to_dict()
            story["category_selection_reason"] = selection.selection_reason
            result["steps"].append("story_generated")
            result["story_project_id"] = story.get("story_project_id")

            story_id = story["story_project_id"]
            work_dir = self.settings.output_dir / f"story_{story_id:03d}"
            output_mgr = OutputManager(work_dir)
            output_mgr.dirs["audio"].mkdir(parents=True, exist_ok=True)

            image_paths, image_prompts = self.images.generate_scene_images(
                story, output_mgr.dirs["images"], aspect
            )
            result["steps"].append("images_generated")
            result["scene_count"] = len(image_paths)

            audio_segments = self.voice.render_story_audio(
                story, output_mgr.dirs["audio"], self.settings.default_language
            )
            result["steps"].append("audio_generated")
            result["narration_voice"] = voice_plan.voice_model
            result["voice_plan"] = voice_plan.to_dict()

            sfx_plan = self.audio_director.scene_sfx_hints(selection.category_id, story)
            music_report = self.audio_director.build_selection_report(
                selection.category_id,
                self.audio_director.pick_background_track(selection.category_id, story),
                sfx_plan,
            )

            final_path = output_mgr.dirs["final"] / "final_video.mp4"
            self.video.render(
                story,
                image_paths,
                audio_segments,
                work_dir,
                final_path,
                aspect_ratio=aspect,
            )
            shutil.copy(final_path, work_dir / "final.mp4")
            result["steps"].append("video_rendered")
            result["video_path"] = str(final_path)

            thumb_variants, thumb_concepts, best_thumb = self.thumb_engine.generate(
                story,
                selection.category_id,
                image_paths[0],
                output_mgr.dirs["thumbnail"],
                count=3,
            )
            thumb_hi = thumb_concepts[0].get("hindi_text") if thumb_concepts else None
            seo = self.seo_gen.generate_full_package(
                story,
                self.settings.default_language,
                category_id=selection.category_id,
                topic_research=selection.topic_research,
                thumbnail_text=thumb_hi,
            )
            result["seo"] = seo
            output_mgr.save_story_artifacts(story, seo=seo, image_prompts=image_prompts)

            result["thumbnail_path"] = str(best_thumb)
            result["thumbnail_concepts"] = thumb_concepts
            result["steps"].append("thumbnail_generated")
            result["steps"].append("creative_seo_generated")

            package = {
                "voice_selection": voice_plan.to_dict(),
                "voice_quality": {
                    "score": voice_plan.quality_score,
                    "checks": voice_plan.quality_checks,
                    "sample_path": voice_plan.sample_path,
                },
                "music_selection": music_report,
                "sound_effects": sfx_plan,
                "thumbnail_concepts": thumb_concepts,
                "thumbnail_final_path": str(best_thumb),
                "title_candidates": seo.get("title_variations"),
                "selected_title": seo.get("selected_title"),
                "description": seo.get("description"),
                "promotional_caption": seo.get("promotional_caption"),
                "hashtags_text": seo.get("hashtags_text"),
                "tags": seo.get("tags"),
                "pinned_comment": seo.get("pinned_comment"),
                "chapters": seo.get("chapters"),
                "seo_report": seo.get("seo_report"),
                "category_selection": result["category"],
            }
            CreativePackageWriter(work_dir).save_all(package)
            result["creative_package_dir"] = str(work_dir / "creative_package")
            result["steps"].append("creative_package_saved")

            probe = self.video.probe(final_path)
            duration = float(probe.get("format", {}).get("duration", 0))
            result["duration_sec"] = duration
            vstreams = [s for s in probe.get("streams", []) if s.get("codec_type") == "video"]
            if vstreams:
                result["resolution"] = f"{vstreams[0].get('width')}x{vstreams[0].get('height')}"

            qc_min = target * 0.65 if not is_short else 5
            qc_max = target * 1.25 if not is_short else 120
            qc = self.qc.inspect_video(
                final_path,
                expected_aspect=aspect,
                min_duration=qc_min,
                max_duration=qc_max,
                thumbnail_path=best_thumb,
                title=seo["recommended_title"],
                story_complete=bool(story.get("ending")),
                language=self.settings.default_language,
            )
            result["qc"] = qc.to_dict()

            with session_scope() as session:
                repo = Repository(session)
                asset = repo.create_video_asset(
                    story_id=story_id,
                    local_path=str(final_path),
                    thumbnail_path=str(best_thumb),
                    aspect_ratio=aspect,
                    qc_passed=qc.passed,
                    qc_report=qc.to_dict(),
                )
                result["video_asset_id"] = asset.id
                repo.audit(
                    "creative_decisions",
                    "video",
                    str(asset.id),
                    {
                        "category": result["category"],
                        "voice": voice_plan.to_dict(),
                        "title": seo.get("recommended_title"),
                        "thumbnail": str(best_thumb),
                    },
                )

            if not qc.passed:
                self.notify.send("Quality check failed", str(qc.critical_failures))
                raise RuntimeError(f"QC failed: {qc.critical_failures}")

            result["steps"].append("qc_passed")
            self.calendar.mark_status(
                story_id,
                "generated",
                category_id=selection.category_id,
                video_path=str(final_path),
            )

            if upload:
                privacy = self.settings.privacy_mode
                publish_at = None
                if self.settings.publishing_mode == "schedule":
                    publish_at = self.scheduler.next_publish_time()
                    if privacy == "private":
                        privacy = "public"
                result["scheduled_publish_at"] = (
                    publish_at.isoformat() if publish_at else None
                )

                upload_row = self.uploader.upload_video(
                    result["video_asset_id"],
                    final_path,
                    {
                        "title": seo["recommended_title"],
                        "description": seo.get("description", ""),
                        "tags": seo.get("tags", []),
                        "category_id": seo.get("category_id", "24"),
                    },
                    privacy=privacy,
                    publish_at=publish_at,
                    thumbnail_path=best_thumb,
                )
                result["youtube_video_id"] = upload_row["youtube_video_id"]
                result["youtube_url"] = upload_row["youtube_url"]
                result["steps"].append("uploaded")
                self.calendar.mark_status(story_id, "published", youtube_url=upload_row["youtube_url"])
                self.notify.send("Video uploaded", f"{upload_row['youtube_url']} ({privacy})")
            else:
                self.notify.send("Video generated", str(final_path))

            if job_id:
                self.jobs.finish(job_id, True)
            return result

        except Exception as exc:
            logger.exception("Pipeline failed")
            if job_id:
                self.jobs.finish(job_id, False, str(exc))
            self.notify.send("Pipeline failed", str(exc))
            raise
