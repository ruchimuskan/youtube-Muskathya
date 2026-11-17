"""
Re-render audio + video for an existing story (story_014) with the double-voice fix.
Usage: .venv/bin/python scripts/rerender_story_audio.py --story-id 14
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

# Make sure app package is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings
from app.voice.dialogue_manager import DialogueManager
from app.voice.voice_director import VoiceDirector
from app.video.video_editor import VideoEditor


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--story-id", type=int, required=True)
    args = parser.parse_args()

    settings = get_settings()
    story_id = args.story_id
    work_dir = settings.output_dir / f"story_{story_id:03d}"
    story_path = work_dir / "story.json"
    if not story_path.exists():
        sys.exit(f"story.json not found at {story_path}")

    payload = json.loads(story_path.read_text(encoding="utf-8"))
    story = payload.get("story") or payload
    language = story.get("language", "hi")
    category_id = story.get("content_category_id", "moral")

    print(f"[1/4] Story loaded: '{story.get('title')}' — {len(story.get('scenes', []))} scenes")

    # ── 1. Plan voice ──────────────────────────────────────────────────────────
    vp = VoiceDirector().plan(category_id, story)
    story["voice_plan"] = vp.to_dict()
    print(f"[2/4] Voice plan: {vp.gender} / {vp.voice_model} / scale={vp.length_scale:.2f}")

    # ── 2. Re-render audio (with double-voice fix) ─────────────────────────────
    audio_dir = work_dir / "audio_rerender"
    if audio_dir.exists():
        shutil.rmtree(audio_dir)
    audio_dir.mkdir(parents=True)

    dm = DialogueManager()
    segments = dm.render_story_audio(story, audio_dir, language)
    total_dur = sum(s.duration_sec for s in segments)
    skipped = [s for s in segments if s.kind == "dialogue"]
    print(
        f"[2/4] Audio done: {len(segments)} segments, {total_dur:.1f}s total"
        f" | {len(skipped)} dialogue segments kept"
    )

    # ── 3. Re-render video ─────────────────────────────────────────────────────
    images = sorted((work_dir / "images").glob("scene_*.png"))
    if not images:
        sys.exit("No scene images found in output/story_014/images/")
    print(f"[3/4] Rendering video with {len(images)} images …")

    final_dir = work_dir / "final"
    final_dir.mkdir(exist_ok=True)
    output_path = final_dir / "final_video.mp4"

    editor = VideoEditor()
    editor.render(
        story=story,
        images=images,
        audio_segments=segments,
        work_dir=work_dir,
        output_path=output_path,
        aspect_ratio="16:9",
    )
    size_mb = output_path.stat().st_size / 1024 / 1024
    print(f"[3/4] Video rendered: {output_path}  ({size_mb:.1f} MB)")

    # ── 4. Done ────────────────────────────────────────────────────────────────
    print()
    print("✅ Re-render complete!")
    print(f"   Video : {output_path}")
    print()
    print("Now run to upload:")
    print(f"  .venv/bin/python -m app.main publish --story-id {story_id} --upload --privacy public")


if __name__ == "__main__":
    main()
