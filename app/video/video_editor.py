from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from app.config import get_settings
from app.utils.media_bins import probe_media_json, resolve_ffmpeg_bin
from app.video.audio_mixer import AudioMixer
from app.video.motion_presets import zoompan_filter
from app.video.subtitle_generator import SubtitleGenerator
from app.voice.dialogue_manager import AudioSegment

logger = logging.getLogger(__name__)


class VideoEditor:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.subtitles = SubtitleGenerator()
        self.mixer = AudioMixer()
        self._ffmpeg = resolve_ffmpeg_bin(self.settings)

    def _concat_audio(self, segments: list[AudioSegment], work_dir: Path) -> tuple[Path, list[tuple[int, float]]]:
        list_file = work_dir / "audio_list.txt"
        scene_durations: list[tuple[int, float]] = []
        lines = []
        for seg in segments:
            lines.append(f"file '{seg.path.resolve()}'")
            scene_durations.append((seg.scene_number, seg.duration_sec))
        list_file.write_text("\n".join(lines), encoding="utf-8")

        merged = work_dir / "narration_full.wav"
        cmd = [
            self._ffmpeg,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-c",
            "copy",
            str(merged),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return merged, scene_durations

    def _build_slideshow(
        self,
        images: list[Path],
        segment_plan: list[tuple[int, float]],
        work_dir: Path,
        aspect_ratio: str,
    ) -> Path:
        scene_totals: dict[int, float] = {}
        for sn, dur in segment_plan:
            scene_totals[sn] = scene_totals.get(sn, 0.0) + dur

        size = "1080x1920" if aspect_ratio == "9:16" else "1920x1080"
        fps = self.settings.video_fps
        fade = self.settings.scene_crossfade_sec
        video_parts: list[Path] = []

        for idx, img in enumerate(images):
            sn = int(img.stem.split("_")[1])
            dur = max(scene_totals.get(sn, 3.0), 1.5)
            motion = zoompan_filter(size, dur, fps, idx)
            fade_out_st = max(dur - fade, 0.1)
            vf = f"{motion},format=yuv420p,fade=t=in:st=0:d={fade},fade=t=out:st={fade_out_st}:d={fade}"

            part = work_dir / f"part_{sn}.mp4"
            cmd = [
                self._ffmpeg,
                "-y",
                "-loop",
                "1",
                "-i",
                str(img),
                "-vf",
                vf,
                "-t",
                str(dur),
                "-r",
                str(fps),
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                "20",
                "-pix_fmt",
                "yuv420p",
                str(part),
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            video_parts.append(part)

        concat_list = work_dir / "video_concat.txt"
        concat_list.write_text(
            "\n".join(f"file '{p.resolve()}'" for p in video_parts),
            encoding="utf-8",
        )
        silent_video = work_dir / "silent_slideshow.mp4"
        subprocess.run(
            [
                self._ffmpeg,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_list),
                "-c",
                "copy",
                str(silent_video),
            ],
            check=True,
            capture_output=True,
        )
        return silent_video

    def _subtitle_filter(self, sub_path: Path) -> str:
        esc = str(sub_path.resolve()).replace("\\", "\\\\").replace(":", "\\:")
        font_dir = self.settings.subtitle_font_path.parent.resolve()
        if sub_path.suffix.lower() == ".ass":
            return f"subtitles='{esc}':fontsdir='{font_dir}'"
        return f"subtitles='{esc}'"

    def render(
        self,
        story: dict,
        images: list[Path],
        audio_segments: list[AudioSegment],
        work_dir: Path,
        output_path: Path,
        *,
        aspect_ratio: str = "16:9",
        srt_path: Path | None = None,
    ) -> Path:
        work_dir.mkdir(parents=True, exist_ok=True)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        merged_audio, scene_durations = self._concat_audio(audio_segments, work_dir)
        final_audio = self.mixer.mix_narration_with_bgm(merged_audio, work_dir, story)
        silent = self._build_slideshow(images, scene_durations, work_dir, aspect_ratio)

        sub_base = srt_path or work_dir / "subtitles" / "subtitles_hi"
        sub_base.parent.mkdir(parents=True, exist_ok=True)
        ass_path = self.subtitles.build_from_story(
            story, scene_durations, sub_base, use_ass=True
        )
        self.subtitles.build_from_story(
            story, scene_durations, sub_base.with_suffix(".srt"), use_ass=False
        )

        vf = self._subtitle_filter(ass_path)
        cmd = [
            self._ffmpeg,
            "-y",
            "-i",
            str(silent),
            "-i",
            str(final_audio),
            "-vf",
            vf,
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "20",
            "-r",
            str(self.settings.video_fps),
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            str(output_path),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path

    def probe(self, video_path: Path) -> dict:
        return probe_media_json(self.settings, video_path)
