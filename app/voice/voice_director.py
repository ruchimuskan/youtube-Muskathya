from __future__ import annotations

import logging
import wave
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.content.categories import get_category
from app.content.category_config import load_category_config

logger = logging.getLogger(__name__)

VOICE_PROFILES: dict[str, dict[str, Any]] = {
    "horror": {"gender": "male", "length_scale": 1.18, "style": "deep slow suspense, pauses"},
    "emotional": {"gender": "male", "length_scale": 1.28, "style": "warm heartfelt"},
    "moral": {"gender": "male", "length_scale": 1.25, "style": "friendly clear conversational"},
    "kids": {"gender": "female", "length_scale": 1.1, "style": "lively simple Hindi"},
    "royal": {"gender": "male", "length_scale": 1.22, "style": "grand storyteller dramatic"},
    "motivational": {"gender": "male", "length_scale": 1.2, "style": "confident energetic"},
    "animal": {"gender": "female", "length_scale": 1.15, "style": "friendly expressive"},
}


@dataclass
class VoicePlan:
    profile: str
    gender: str
    voice_model: str
    length_scale: float
    style_notes: str
    sample_path: str | None
    quality_score: float
    quality_checks: dict[str, bool]
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class VoiceDirector:
    def __init__(self) -> None:
        self.settings = get_settings()

    def plan(self, category_id: str, story: dict[str, Any]) -> VoicePlan:
        config = load_category_config()
        category = get_category(category_id)
        profile_key = category.voice_profile
        profile = VOICE_PROFILES.get(profile_key, VOICE_PROFILES["moral"])

        gender = config.get("narrator_gender_override") or self.settings.narrator_gender
        if profile.get("gender"):
            gender = profile["gender"]

        voice_model = (
            self.settings.piper_voice_hi_female
            if gender == "female"
            else self.settings.piper_voice_hi_male
        )
        if not (self.settings.piper_voices_dir / f"{voice_model}.onnx").exists():
            voice_model = self.settings.piper_voice_hi_male
            gender = "male"

        if not (self.settings.piper_voices_dir / f"{voice_model}.onnx").exists():
            raise FileNotFoundError(
                f"Hindi Piper voice not found for {voice_model}. "
                f"Place ONNX in {self.settings.piper_voices_dir}"
            )

        intensity = story.get("suspense_level", 5)
        if intensity > 7:
            length_scale = profile["length_scale"] * 1.05
        else:
            length_scale = profile["length_scale"]

        reason = (
            f"Category {category.name_hi} → profile {profile_key}, gender {gender}, "
            f"model {voice_model}, scale {length_scale:.2f}"
        )

        sample_path, checks, score = self._optional_sample_test(voice_model, gender, length_scale)

        return VoicePlan(
            profile=profile_key,
            gender=gender,
            voice_model=voice_model,
            length_scale=length_scale,
            style_notes=profile["style"],
            sample_path=sample_path,
            quality_score=score,
            quality_checks=checks,
            reason=reason,
        )

    def _optional_sample_test(
        self, voice_model: str, gender: str, length_scale: float
    ) -> tuple[str | None, dict[str, bool], float]:
        from app.voice.piper_engine import PiperEngine

        sample_dir = self.settings.data_dir / "voice_samples"
        sample_dir.mkdir(parents=True, exist_ok=True)
        out = sample_dir / f"{voice_model}_sample.wav"
        checks: dict[str, bool] = {
            "model_file_exists": (self.settings.piper_voices_dir / f"{voice_model}.onnx").exists(),
            "piper_available": PiperEngine().is_available(),
        }
        score = 0.0
        if not checks["model_file_exists"] or not checks["piper_available"]:
            return None, checks, score

        try:
            engine = PiperEngine()
            engine.synthesize(
                "यह हिंदी आवाज़ का परीक्षण है।",
                out,
                language="hi",
                gender=gender,
                length_scale=length_scale,
            )
            with wave.open(str(out), "rb") as wf:
                dur = wf.getnframes() / float(wf.getframerate())
            checks["sample_created"] = out.exists() and out.stat().st_size > 2000
            checks["hindi_sample_ok"] = dur > 0.8
            checks["no_clipping_proxy"] = out.stat().st_size < 5_000_000
            score = sum(1 for v in checks.values() if v) / max(len(checks), 1)
            return str(out), checks, round(score, 2)
        except Exception as exc:
            logger.warning("Voice sample test failed: %s", exc)
            checks["sample_created"] = False
            return None, checks, score
