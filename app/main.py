from __future__ import annotations

import argparse
import logging
import sys

from app.database import Repository, session_scope


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def cmd_init_db() -> None:
    with session_scope() as session:
        Repository(session).init_db()
    print("Database initialized.")


def cmd_serve() -> None:
    import uvicorn

    from app.config import get_settings
    from app.dashboard.app import create_app

    s = get_settings()
    uvicorn.run(create_app(), host=s.dashboard_host, port=s.dashboard_port)


def cmd_generate(args: argparse.Namespace) -> None:
    from app.automation.pipeline import ContentPipeline

    pipeline = ContentPipeline()
    result = pipeline.run(
        upload=args.upload,
        idempotency_key=args.idempotency_key,
        category_id=getattr(args, "category", None),
        topic_hint=getattr(args, "topic", None),
    )
    print(result)


def cmd_test_ai() -> None:
    from app.ai.providers.router import LLMRouter
    from app.config.settings import get_settings

    get_settings.cache_clear()
    s = get_settings()
    if not s.cloudflare_account_id or not s.cloudflare_api_token:
        print("Missing CLOUDFLARE_ACCOUNT_ID or CLOUDFLARE_API_TOKEN in .env")
        raise SystemExit(1)
    router = LLMRouter()
    reply = router.complete("Reply with exactly: OK", system="Be brief.")
    print(f"Provider: {reply.provider}")
    print(f"Model: {reply.model}")
    print(f"Response: {reply.text[:500]}")


def cmd_test_tts() -> None:
    from pathlib import Path

    from app.config import get_settings
    from app.voice.hindi_text import prepare_hindi_tts
    from app.voice.segment_synthesizer import SegmentSynthesizer
    from app.voice.voice_quality import HINDI_TEST_SENTENCES, run_voice_quality_report

    acceptance = [
        "रोहित की माँ ने कहा, यहाँ आओ। रोहित ने पूछा, क्या हुआ माँ?",
        "एक दिन रोहित अपनी माँ के साथ बाजार गया। वहाँ उसने एक सुंदर खिलौना देखा।",
    ]
    out_dir = get_settings().data_dir / "tts_acceptance"
    out_dir.mkdir(parents=True, exist_ok=True)
    synth = SegmentSynthesizer()
    for i, text in enumerate(acceptance):
        prep = prepare_hindi_tts(text)
        print(f"\n=== Acceptance {i} ===")
        print("Original:", text)
        print("Segments:", prep.segments)
        wav = out_dir / f"acceptance_{i}.wav"
        _, _, records = synth.synthesize_full(text, wav, scene_number=900 + i)
        print("Output:", wav, "duration", synth.engine.wav_duration(wav))
        for r in records:
            if r.get("segment_id") != "merged":
                print(" ", r.get("segment_id"), r.get("segment_text"), r.get("verify_passed"))

    report = run_voice_quality_report()
    print("\nVoice quality:", report["passed"], "/", report["total"])
    print("Report:", get_settings().data_dir / "voice_quality/voice_quality_report.json")


def cmd_publish(args: argparse.Namespace) -> None:
    from app.automation.publish_story import publish_story

    result = publish_story(args.story_id, upload=args.upload, privacy=args.privacy)
    print(result)


def cmd_scheduler() -> None:
    from app.automation.daily_scheduler import start_blocking_scheduler

    start_blocking_scheduler()


def cmd_oauth_url() -> None:
    from app.youtube.oauth import YouTubeOAuth

    oauth = YouTubeOAuth()
    url = oauth.start_authorization()
    print("Open this URL in your browser to authorize (keep `python -m app.main serve` running):")
    print(url)


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    parser = argparse.ArgumentParser(description="YouTube Channel Manager")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init-db", help="Create SQLite tables")
    sub.add_parser("serve", help="Run dashboard + OAuth callback server")

    gen = sub.add_parser("generate", help="Run content pipeline")
    gen.add_argument("--upload", action="store_true", help="Upload after QC (private by default)")
    gen.add_argument("--idempotency-key", default=None)
    gen.add_argument(
        "--category",
        default=None,
        help="Override auto category (e.g. moral, horror_mystery, village_life)",
    )
    gen.add_argument(
        "--topic",
        default=None,
        help="Story topic hint in Hindi (e.g. भगवान शिव और भक्त की कहानी)",
    )

    sub.add_parser("oauth-url", help="Print Google OAuth authorization URL")
    sub.add_parser("test-ai", help="Test Cloudflare Workers AI connection")
    sub.add_parser("test-tts", help="Hindi TTS acceptance + voice quality report")
    pub = sub.add_parser("publish", help="Finish SEO/thumbnail and upload an existing story video")
    pub.add_argument("--story-id", type=int, required=True)
    pub.add_argument("--upload", action="store_true", help="Upload to YouTube")
    pub.add_argument("--privacy", default="public", choices=["public", "unlisted", "private"])
    sub.add_parser(
        "scheduler",
        help="Daily auto generate+upload (PIPELINE_DAILY_RUN_* → YouTube publish PUBLISH_HOUR)",
    )

    args = parser.parse_args(argv)
    if args.command == "init-db":
        cmd_init_db()
    elif args.command == "serve":
        cmd_serve()
    elif args.command == "generate":
        cmd_generate(args)
    elif args.command == "oauth-url":
        cmd_oauth_url()
    elif args.command == "test-ai":
        cmd_test_ai()
    elif args.command == "test-tts":
        cmd_test_tts()
    elif args.command == "publish":
        cmd_publish(args)
    elif args.command == "scheduler":
        cmd_scheduler()
    else:
        parser.print_help()
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
