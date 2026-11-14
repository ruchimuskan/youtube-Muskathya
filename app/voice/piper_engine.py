from __future__ import annotations

import logging
import shutil
import subprocess
import wave
from pathlib import Path

from app.config import get_settings

logger = logging.getLogger(__name__)


class PiperEngine:
    """Local Piper TTS wrapper."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def _voice_model_path(self, voice_name: str) -> Path:
        return self.settings.piper_voices_dir / f"{voice_name}.onnx"

    def resolve_voice(self, language: str, gender: str) -> str:
        gender = gender.lower()
        if language == "hi":
            male = self.settings.piper_voice_hi_male
            female = self.settings.piper_voice_hi_female
            if gender != "male" and not self._voice_model_path(female).exists():
                return male
            return male if gender == "male" else female
        return (
            self.settings.piper_voice_en_male
            if gender == "male"
            else self.settings.piper_voice_en_female
        )

    def _piper_bin(self) -> str | None:
        if shutil.which(self.settings.piper_bin):
            return shutil.which(self.settings.piper_bin)
        for candidate in (
            Path.cwd() / ".local" / "piper" / "piper",
            self.settings.piper_voices_dir.parent / "bin" / "piper",
            Path.cwd() / ".venv" / "bin" / "piper",
        ):
            if candidate.exists():
                return str(candidate)
        return None

    def is_available(self) -> bool:
        if self._piper_bin() is not None and self._voice_model_path(
            self.resolve_voice("hi", "male")
        ).exists():
            return True
        if self.settings.allow_say_fallback and shutil.which("say"):
            return True
        return False

    def _synthesize_macos_say(self, text: str, output_path: Path, language: str) -> Path:
        aiff = output_path.with_suffix(".aiff")
        voice = "Rishi" if language == "hi" else "Samantha"
        proc = subprocess.run(
            ["say", "-v", voice, "-o", str(aiff), text],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            subprocess.run(["say", "-o", str(aiff), text], check=True)
        ffmpeg = shutil.which(self.settings.ffmpeg_bin)
        if not ffmpeg:
            try:
                import imageio_ffmpeg

                ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
            except Exception:
                ffmpeg = None
        if not ffmpeg:
            raise RuntimeError("Need ffmpeg to convert say output to wav")
        subprocess.run(
            [ffmpeg, "-y", "-i", str(aiff), str(output_path)],
            check=True,
            capture_output=True,
        )
        aiff.unlink(missing_ok=True)
        return output_path

    def synthesize(
        self,
        text: str,
        output_path: Path,
        *,
        language: str = "hi",
        gender: str = "male",
        length_scale: float = 1.0,
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        voice = self.resolve_voice(language, gender)
        model = self._voice_model_path(voice)
        bin_path = self._piper_bin()
        if not model.exists():
            if self.settings.allow_say_fallback and shutil.which("say"):
                logger.warning("Piper model missing; using macOS say fallback")
                return self._synthesize_macos_say(text, output_path, language)
            raise FileNotFoundError(
                f"Piper voice model not found: {model}. Download ONNX models into {self.settings.piper_voices_dir}"
            )

        if not bin_path:
            if self.settings.allow_say_fallback and shutil.which("say"):
                logger.warning("Piper binary missing; using macOS say fallback")
                return self._synthesize_macos_say(text, output_path, language)
            raise FileNotFoundError(
                "Piper binary not found. Install: pip install piper-tts"
            )

        input_file = output_path.with_suffix(".input.txt")
        input_file.write_text(text, encoding="utf-8")

        cmd = [
            bin_path,
            "--model",
            str(model),
            "--output_file",
            str(output_path),
            "--length_scale",
            str(length_scale),
            "--input_file",
            str(input_file),
        ]
        config = model.with_suffix(".onnx.json")
        if config.exists():
            cmd.extend(["--config", str(config)])

        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            if self.settings.allow_say_fallback and shutil.which("say"):
                logger.warning("Piper failed (%s); using say fallback", proc.stderr[:200])
                return self._synthesize_macos_say(text, output_path, language)
            raise RuntimeError(f"Piper failed: {proc.stderr}")

        if not output_path.exists():
            raise RuntimeError("Piper did not produce output file")

        return output_path

    @staticmethod
    def wav_duration(path: Path) -> float:
        with wave.open(str(path), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            return frames / float(rate)
