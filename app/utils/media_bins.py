from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

from app.config.settings import Settings


def resolve_ffmpeg_bin(settings: Settings) -> str:
    if shutil.which(settings.ffmpeg_bin):
        return settings.ffmpeg_bin
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    raise FileNotFoundError(
        "ffmpeg not found. Install via brew, or: pip install imageio-ffmpeg"
    )


def resolve_ffprobe_bin(settings: Settings) -> str:
    if shutil.which(settings.ffprobe_bin):
        return settings.ffprobe_bin
    ffmpeg = Path(resolve_ffmpeg_bin(settings))
    sibling = ffmpeg.parent / "ffprobe"
    if sibling.exists():
        return str(sibling)
    return resolve_ffmpeg_bin(settings)


def probe_media_json(settings: Settings, path: Path) -> dict:
    """Use ffprobe if available; otherwise parse ffmpeg -i stderr."""
    ffmpeg = resolve_ffmpeg_bin(settings)
    ffprobe = resolve_ffprobe_bin(settings)
    if ffprobe != ffmpeg and shutil.which("ffprobe"):
        try:
            out = subprocess.check_output(
                [
                    ffprobe,
                    "-v",
                    "error",
                    "-show_format",
                    "-show_streams",
                    "-of",
                    "json",
                    str(path),
                ],
                text=True,
            )
            return json.loads(out)
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            pass
    proc = subprocess.run(
        [ffmpeg, "-hide_banner", "-i", str(path)],
        capture_output=True,
        text=True,
    )
    text = proc.stderr
    duration_m = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", text)
    if not duration_m:
        raise RuntimeError("Could not probe media duration")
    h, m, s = duration_m.groups()
    duration = int(h) * 3600 + int(m) * 60 + float(s)
    has_video = "Video:" in text
    has_audio = "Audio:" in text
    vstreams = []
    if has_video:
        res = re.search(r"(\d{3,4})x(\d{3,4})", text)
        if res:
            vstreams.append(
                {
                    "codec_type": "video",
                    "width": int(res.group(1)),
                    "height": int(res.group(2)),
                }
            )
    ast = [{"codec_type": "audio"}] if has_audio else []
    return {
        "format": {"duration": str(duration)},
        "streams": vstreams + ast,
    }
