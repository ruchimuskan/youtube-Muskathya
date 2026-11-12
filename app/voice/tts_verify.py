from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from app.config import get_settings
from app.voice.hindi_text import devanagari_char_count

logger = logging.getLogger(__name__)


@dataclass
class TTSVerifyResult:
    passed: bool
    expected_chars: int
    duration_sec: float
    min_expected_duration: float
    transcribed: str | None
    missing_prefix: bool
    notes: list[str]

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "expected_chars": self.expected_chars,
            "duration_sec": self.duration_sec,
            "min_expected_duration": self.min_expected_duration,
            "transcribed": self.transcribed,
            "missing_prefix": self.missing_prefix,
            "notes": self.notes,
        }


def min_duration_for_text(text: str, *, sec_per_char: float = 0.055) -> float:
    n = max(devanagari_char_count(text), len(text.split()) * 2)
    return max(0.35, n * sec_per_char)


def verify_segment(
    original_text: str,
    wav_path: Path,
    duration_sec: float,
    *,
    transcribed: str | None = None,
) -> TTSVerifyResult:
    notes: list[str] = []
    min_dur = min_duration_for_text(original_text)
    passed = duration_sec >= min_dur * 0.65 and wav_path.exists() and wav_path.stat().st_size > 500

    missing_prefix = False
    if transcribed and get_settings().tts_use_whisper_verify:
        ot = original_text.strip()
        tr = transcribed.strip()
        if ot and tr and not tr.startswith(ot[: max(3, len(ot) // 4)]):
            missing_prefix = True
            notes.append("transcription may miss sentence start (whisper)")
        if devanagari_char_count(ot) > 8 and devanagari_char_count(tr) < devanagari_char_count(ot) * 0.45:
            passed = False
            notes.append("transcription much shorter than source")

    if duration_sec < min_dur * 0.65:
        passed = False
        notes.append(f"audio too short for text (got {duration_sec:.2f}s, need ~{min_dur:.2f}s)")

    return TTSVerifyResult(
        passed=passed,
        expected_chars=devanagari_char_count(original_text),
        duration_sec=duration_sec,
        min_expected_duration=min_dur,
        transcribed=transcribed,
        missing_prefix=missing_prefix,
        notes=notes,
    )


def try_transcribe_hi(wav_path: Path) -> str | None:
    try:
        from faster_whisper import WhisperModel

        model = WhisperModel("base", device="cpu", compute_type="int8")
        segments, _ = model.transcribe(str(wav_path), language="hi")
        return "".join(s.text for s in segments).strip()
    except Exception as exc:
        logger.debug("Whisper transcription skipped: %s", exc)
        return None
