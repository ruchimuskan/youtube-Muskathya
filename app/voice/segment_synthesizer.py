from __future__ import annotations

import logging
import subprocess
import wave
from pathlib import Path

from app.config import get_settings
from app.utils.media_bins import resolve_ffmpeg_bin
from app.voice.hindi_text import HindiTTSInput, prepare_hindi_tts
from app.voice.piper_engine import PiperEngine
from app.voice.tts_logger import TTSLogger
from app.voice.tts_verify import try_transcribe_hi, verify_segment

logger = logging.getLogger(__name__)


class SegmentSynthesizer:
    """Sentence/clause-level Hindi TTS with concat and verification."""

    def __init__(self, engine: PiperEngine | None = None) -> None:
        self.engine = engine or PiperEngine()
        self.settings = get_settings()
        self._ffmpeg = resolve_ffmpeg_bin(self.settings)

    def synthesize_full(
        self,
        text: str,
        output_path: Path,
        *,
        language: str = "hi",
        gender: str = "male",
        length_scale: float = 1.0,
        scene_number: int | None = None,
        kind: str = "narration",
        tts_log: TTSLogger | None = None,
        verify: bool = True,
    ) -> tuple[Path, HindiTTSInput, list[dict]]:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        prepared = prepare_hindi_tts(text)
        work = output_path.parent / f"_tts_parts_{output_path.stem}"
        work.mkdir(parents=True, exist_ok=True)

        part_paths: list[Path] = []
        records: list[dict] = []

        for idx, segment in enumerate(prepared.segments):
            seg_id = f"{scene_number or 0:03d}_{kind}_{idx:02d}"
            part = work / f"{seg_id}.wav"
            self._run_piper(segment, part, language, gender, length_scale)

            dur = self.engine.wav_duration(part)
            transcribed = (
                try_transcribe_hi(part)
                if verify and self.settings.tts_use_whisper_verify
                else None
            )
            v = verify_segment(segment, part, dur, transcribed=transcribed)

            rec = {
                "scene_number": scene_number,
                "kind": kind,
                "segment_id": seg_id,
                "original_text": prepared.original,
                "segment_text": segment,
                "normalized_full": prepared.normalized,
                "segments": prepared.segments,
                "tts_input": segment,
                "audio_path": str(part),
                "duration_sec": dur,
                "verify_passed": v.passed,
                "verify": v.to_dict(),
                "provider": "piper",
                "model": self.engine.resolve_voice(language, gender),
                "transcribed": transcribed,
            }
            records.append(rec)
            if tts_log:
                tts_log.log_segment(rec)

            if not v.passed:
                alt = segment.replace(",", " — ").replace("،", " — ")
                if alt != segment:
                    self._run_piper(alt, part, language, gender, length_scale)
                    dur = self.engine.wav_duration(part)
                    v = verify_segment(segment, part, dur)
                    rec["retry_input"] = alt
                    rec["duration_sec"] = dur
                    rec["verify_passed"] = v.passed
                    rec["verify"] = v.to_dict()
                if not v.passed:
                    raise RuntimeError(
                        f"TTS segment failed ({seg_id}): {segment!r} — {v.notes}"
                    )

            part_paths.append(part)

        if len(part_paths) == 1:
            import shutil

            shutil.copy(part_paths[0], output_path)
        else:
            self._concat_wavs(part_paths, output_path, pause_ms=120)

        total_dur = self.engine.wav_duration(output_path)
        full_check = verify_segment(prepared.normalized, output_path, total_dur)
        records.append(
            {
                "segment_id": "merged",
                "audio_path": str(output_path),
                "duration_sec": total_dur,
                "verify_passed": full_check.passed,
                "verify": full_check.to_dict(),
            }
        )
        return output_path, prepared, records

    def _run_piper(
        self,
        text: str,
        output_path: Path,
        language: str,
        gender: str,
        length_scale: float,
    ) -> None:
        voice = self.engine.resolve_voice(language, gender)
        model = self.engine._voice_model_path(voice)
        bin_path = self.engine._piper_bin()
        if not bin_path:
            raise FileNotFoundError("Piper binary missing")

        input_file = output_path.with_suffix(".txt")
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
            raise RuntimeError(f"Piper failed: {proc.stderr}")
        if not output_path.exists():
            raise RuntimeError("Piper produced no output")

    def _concat_wavs(self, parts: list[Path], out: Path, pause_ms: int = 120) -> None:
        """Concat with short silence between clauses."""
        if not parts:
            raise ValueError("No audio parts")
        with wave.open(str(parts[0]), "rb") as w0:
            nch, sampwidth, framerate = w0.getnchannels(), w0.getsampwidth(), w0.getframerate()

        silence_frames = int(framerate * pause_ms / 1000)
        silence = (b"\x00" * sampwidth) * silence_frames * nch

        list_file = out.parent / f"{out.stem}_concat.txt"
        intermediate: list[Path] = []
        for i, p in enumerate(parts):
            intermediate.append(p)
            if i < len(parts) - 1 and pause_ms > 0:
                pause_path = out.parent / f"pause_{i}.wav"
                with wave.open(str(pause_path), "wb") as pw:
                    pw.setnchannels(nch)
                    pw.setsampwidth(sampwidth)
                    pw.setframerate(framerate)
                    pw.writeframes(silence)
                intermediate.append(pause_path)

        lines = [f"file '{p.resolve()}'" for p in intermediate]
        list_file.write_text("\n".join(lines), encoding="utf-8")
        subprocess.run(
            [
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
                str(out),
            ],
            check=True,
            capture_output=True,
        )
