from __future__ import annotations

from pathlib import Path

from app.config import get_settings
from app.utils.hindi_text import split_subtitle_chunks


def format_srt_time(seconds: float) -> str:
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{ms:03d}"


def format_ass_time(seconds: float) -> str:
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{hrs}:{mins:02d}:{secs:02d}.{cs:02d}"


class SubtitleGenerator:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _scene_text(self, scene: dict) -> str:
        parts = []
        if scene.get("narration"):
            parts.append(scene["narration"])
        for d in scene.get("dialogue") or []:
            line = (d.get("line") or "").strip()
            if line:
                parts.append(f"{d.get('character')}: {line}")
        return " ".join(parts).strip()

    def build_from_story(
        self,
        story: dict,
        scene_durations: list[tuple[int, float]],
        path: Path,
        *,
        use_ass: bool = True,
    ) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        scenes_by_num = {s.get("scene_number"): s for s in story.get("scenes", [])}

        cues: list[tuple[float, float, str]] = []
        cursor = 0.0
        for scene_num, duration in scene_durations:
            scene = scenes_by_num.get(scene_num, {})
            text = self._scene_text(scene)
            if not text:
                cursor += duration
                continue
            chunks = split_subtitle_chunks(text, max_chars=self.settings.subtitle_max_chars)
            if not chunks:
                cursor += duration
                continue
            slice_dur = duration / len(chunks)
            for chunk in chunks:
                start = cursor
                end = cursor + slice_dur
                cues.append((start, end, chunk))
                cursor = end

        if use_ass:
            return self._write_ass(cues, path.with_suffix(".ass"))
        return self._write_srt(cues, path)

    def _write_srt(self, cues: list[tuple[float, float, str]], path: Path) -> Path:
        lines: list[str] = []
        for i, (start, end, text) in enumerate(cues, start=1):
            lines.extend(
                [
                    str(i),
                    f"{format_srt_time(start)} --> {format_srt_time(end)}",
                    text.replace("\n", " "),
                    "",
                ]
            )
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    def _write_ass(self, cues: list[tuple[float, float, str]], path: Path) -> Path:
        font = self._resolve_font()
        header = f"""[Script Info]
Title: Hindi Story
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Hindi,{font},48,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,3,1,2,80,80,56,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        events = []
        for start, end, text in cues:
            safe = text.replace("\n", "\\N")
            events.append(
                f"Dialogue: 0,{format_ass_time(start)},{format_ass_time(end)},Hindi,,0,0,0,,{safe}"
            )
        path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")
        return path

    def _resolve_font(self) -> str:
        custom = self.settings.subtitle_font_path
        if custom.exists():
            return custom.stem
        for candidate in (
            "/System/Library/Fonts/Supplemental/NotoSansDevanagari-Regular.ttf",
            "/System/Library/Fonts/KohinoorDevanagari-Regular.ttf",
            "/Library/Fonts/Arial Unicode.ttf",
        ):
            if Path(candidate).exists():
                return Path(candidate).stem
        return "Arial Unicode MS"
