from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    data_dir: Path = Path("./data")
    output_dir: Path = Path("./output")
    log_dir: Path = Path("./logs")
    timezone: str = "Asia/Kolkata"
    emergency_stop: bool = False

    database_url: str = "sqlite:///./data/channel_manager.db"

    ai_provider: Literal["cloudflare", "ollama", "auto"] = "auto"
    ai_cloudflare_daily_limit: int = 9000
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.1:8b"
    cloudflare_account_id: str = ""
    cloudflare_api_token: str = ""
    cloudflare_model: str = "@cf/meta/llama-3.1-8b-instruct-fast"

    default_language: Literal["hi", "en"] = "hi"
    default_genre: str = "moral"
    video_aspect_ratio: Literal["16:9", "9:16"] = "16:9"
    video_min_duration_sec: int = 360
    video_max_duration_sec: int = 600
    video_fps: int = 30
    story_min_scenes: int = 22
    story_max_scenes: int = 40
    max_daily_uploads: int = 1
    privacy_mode: Literal["private", "unlisted", "public"] = "public"
    publishing_mode: Literal["immediate", "schedule"] = "schedule"
    publish_hour: int = 18
    publish_minute: int = 0
    pipeline_daily_run_hour: int = 15
    pipeline_daily_run_minute: int = 0
    shorts_ratio: float = 0.0
    automatic_learning: bool = True
    automatic_improvement: bool = True
    preview_approval_mode: bool = True

    piper_bin: str = "piper"
    piper_voices_dir: Path = Path("./data/voices")
    piper_voice_hi_male: str = "hi_IN-pratham-medium"
    piper_voice_hi_female: str = "hi_IN-priyamvada-medium"
    piper_voice_en_male: str = "en_US-lessac-medium"
    piper_voice_en_female: str = "en_US-amy-medium"
    narrator_gender: Literal["male", "female"] = "male"
    piper_length_scale: float = 1.32
    allow_say_fallback: bool = False
    tts_use_whisper_verify: bool = False

    comfyui_url: str = "http://127.0.0.1:8188"
    image_style: str = (
        "cinematic Indian story illustration, detailed lighting, expressive faces, "
        "rich natural colours, professional composition, no watermark, no text"
    )
    cloudflare_image_enabled: bool = True
    cloudflare_image_model: str = "@cf/stabilityai/stable-diffusion-xl-base-1.0"
    image_negative_prompt: str = (
        "blurry, low quality, watermark, text, logo, cartoon, anime, deformed, ugly, "
        "bad anatomy, extra limbs, missing fingers, fused limbs, duplicate face, "
        "oversaturated, noisy, grayscale"
    )
    image_guidance: float = 7.5
    image_num_steps: int = 20
    image_gen_width: int = 1024
    image_gen_height: int = 576
    image_min_file_bytes: int = 40_000
    image_max_retries: int = 3
    allow_placeholder_images: bool = False
    image_fallback_dir: Path = Path("./data/fallback_images")
    comfyui_enabled: bool = False

    ffmpeg_bin: str = "ffmpeg"
    ffprobe_bin: str = "ffprobe"
    whisper_model: str = "base"
    use_whisper_subtitles: bool = False
    subtitle_max_chars: int = 42
    subtitle_font_path: Path = Path("./data/fonts/NotoSansDevanagari-Regular.ttf")
    background_music_dir: Path = Path("./data/music")
    background_music_volume: float = 0.18
    narration_volume: float = 1.0
    scene_crossfade_sec: float = 0.35

    google_client_secrets_file: Path = Path("./client_secrets.json")
    google_redirect_uri: str = "http://127.0.0.1:8765/oauth2/callback"
    youtube_oauth_token_file: Path = Path("./data/oauth_tokens.json")
    youtube_upload_chunk_size: int = 1_048_576

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    notify_email: str = ""

    dashboard_host: str = "127.0.0.1"
    dashboard_port: int = 8765

    @field_validator("data_dir", "output_dir", "log_dir", mode="before")
    @classmethod
    def _path(cls, v: str | Path) -> Path:
        return Path(v)

    def ensure_dirs(self) -> None:
        for d in (
            self.data_dir,
            self.output_dir,
            self.log_dir,
            self.piper_voices_dir,
            self.image_fallback_dir,
            self.background_music_dir,
            self.subtitle_font_path.parent,
        ):
            d.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.ensure_dirs()
    return s
