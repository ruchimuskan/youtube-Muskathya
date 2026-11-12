from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from app.config import get_settings
from app.voice.piper_engine import PiperEngine
from app.voice.segment_synthesizer import SegmentSynthesizer
from app.voice.tts_logger import TTSLogger

logger = logging.getLogger(__name__)


@dataclass
class AudioSegment:
    path: Path
    duration_sec: float
    scene_number: int
    kind: str  # narration | dialogue | cta


class DialogueManager:
    def __init__(self, engine: PiperEngine | None = None) -> None:
        self.engine = engine or PiperEngine()
        self.segmenter = SegmentSynthesizer(self.engine)
        self.settings = get_settings()

    def _length_scale(self, scene: dict, base: float | None = None) -> float:
        mood = (scene.get("mood") or "").lower()
        base = base if base is not None else self.settings.piper_length_scale
        if "suspense" in mood or "dramatic" in mood:
            return base * 0.95
        if "emotional" in mood:
            return base * 1.08
        return base

    def render_story_audio(
        self,
        story: dict,
        work_dir: Path,
        language: str,
    ) -> list[AudioSegment]:
        work_dir.mkdir(parents=True, exist_ok=True)
        if language == "hi" and not self.engine.is_available():
            raise FileNotFoundError(
                "Hindi Piper TTS is required. Install: pip install piper-tts "
                f"and place voice ONNX in {self.settings.piper_voices_dir}"
            )

        tts_log = TTSLogger(work_dir)
        segments: list[AudioSegment] = []
        characters = {c["name"]: c for c in story.get("characters", [])}
        vp = story.get("voice_plan") or {}
        narrator = vp.get("gender") or self.settings.narrator_gender
        base_scale = float(vp.get("length_scale") or self.settings.piper_length_scale)

        for scene in story.get("scenes", []):
            sn = scene.get("scene_number", 0)
            narration = (scene.get("narration") or "").strip()
            scale = self._length_scale(scene, base_scale)
            if narration:
                out = work_dir / f"scene_{sn:03d}_narration.wav"
                self.segmenter.synthesize_full(
                    narration,
                    out,
                    language=language,
                    gender=narrator,
                    length_scale=scale,
                    scene_number=sn,
                    kind="narration",
                    tts_log=tts_log,
                )
                segments.append(
                    AudioSegment(out, self.engine.wav_duration(out), sn, "narration")
                )

            for i, line in enumerate(scene.get("dialogue") or []):
                name = line.get("character", "unknown")
                text = (line.get("line") or "").strip()
                if not text:
                    continue
                gender = line.get("gender") or characters.get(name, {}).get("gender", "female")
                out = work_dir / f"scene_{sn:03d}_dialogue_{i}.wav"
                self.segmenter.synthesize_full(
                    text,
                    out,
                    language=language,
                    gender=str(gender),
                    length_scale=scale,
                    scene_number=sn,
                    kind=f"dialogue_{i}",
                    tts_log=tts_log,
                )
                segments.append(
                    AudioSegment(out, self.engine.wav_duration(out), sn, "dialogue")
                )

        cta = (story.get("call_to_action") or "").strip()
        if cta and language == "hi":
            sn_cta = (story.get("scenes") or [{}])[-1].get("scene_number", 999)
            out = work_dir / "call_to_action.wav"
            self.segmenter.synthesize_full(
                cta,
                out,
                language=language,
                gender=narrator,
                length_scale=1.0,
                scene_number=sn_cta,
                kind="cta",
                tts_log=tts_log,
            )
            segments.append(AudioSegment(out, self.engine.wav_duration(out), sn_cta, "cta"))

        return segments
