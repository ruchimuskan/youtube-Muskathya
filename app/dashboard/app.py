from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import desc, func, select

from app.ai.performance_analyzer import PerformanceAnalyzer
from app.config import get_settings
from app.database import Repository, session_scope
from app.database.models import (
    LearningRecord,
    MistakeReport,
    VideoAsset,
    VideoPerformanceSnapshot,
    YouTubeUpload,
)
from app.youtube.channel_manager import ChannelManager
from app.content.calendar import ContentCalendar
from app.content.categories import CATEGORIES
from app.content.category_config import load_category_config, save_category_config
from app.youtube.oauth import YouTubeOAuth

TEMPLATES = Path(__file__).parent / "templates"
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(title="YouTube Channel Manager")
    templates = Jinja2Templates(directory=str(TEMPLATES))
    oauth = YouTubeOAuth()

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request):
        with session_scope() as session:
            total_videos = session.scalar(select(func.count()).select_from(VideoAsset)) or 0
            upload_rows = list(
                session.scalars(
                    select(YouTubeUpload).order_by(desc(YouTubeUpload.uploaded_at)).limit(10)
                )
            )
            lesson_rows = list(
                session.scalars(
                    select(LearningRecord).order_by(desc(LearningRecord.created_at)).limit(10)
                )
            )
            channel_row = Repository(session).get_active_channel()

            uploads = [
                {
                    "title": u.title,
                    "upload_status": u.upload_status,
                    "privacy": u.privacy.value if u.privacy else "unknown",
                    "youtube_url": u.youtube_url,
                }
                for u in upload_rows
            ]
            lessons = [{"category": l.category, "lesson": l.lesson} for l in lesson_rows]
            channel = (
                {
                    "channel_title": channel_row.channel_title,
                    "channel_id": channel_row.channel_id,
                }
                if channel_row
                else None
            )

        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "total_videos": total_videos,
                "uploads": uploads,
                "lessons": lessons,
                "channel": channel,
                "oauth_status": oauth.connection_status(),
                "settings": get_settings(),
            },
        )

    @app.get("/oauth/start")
    def oauth_start():
        url = oauth.start_authorization()
        return RedirectResponse(url)

    @app.get("/oauth2/callback")
    def oauth_callback(
        request: Request,
        state: str | None = None,
        code: str | None = None,
        error: str | None = None,
    ):
        if error:
            raise HTTPException(400, f"OAuth error: {error}")
        if not code:
            raise HTTPException(400, "Missing code")
        if not state:
            raise HTTPException(400, "Missing state")
        try:
            oauth.complete_authorization(state, str(request.url))
        except FileNotFoundError as exc:
            raise HTTPException(
                400,
                f"{exc} Start again from the dashboard (do not reload this page).",
            ) from exc
        except Exception as exc:
            logger.exception("OAuth token exchange failed")
            raise HTTPException(400, f"Token exchange failed: {exc}") from exc

        try:
            ChannelManager(oauth).verify_and_save_channel()
        except Exception as exc:
            logger.exception("YouTube channel verification failed")
            raise HTTPException(
                400,
                f"Token saved but channel verify failed: {exc}. Check YouTube Data API is enabled.",
            ) from exc

        return RedirectResponse("/", status_code=303)

    @app.get("/categories", response_class=HTMLResponse)
    def categories_page(request: Request):
        cfg = load_category_config()
        cats = [
            {
                "id": cid,
                "name_hi": c.name_hi,
                "enabled": cid in cfg.get("enabled_categories", []),
                "weight": cfg.get("category_weights", {}).get(cid, c.default_weight),
            }
            for cid, c in CATEGORIES.items()
        ]
        cal = ContentCalendar().upcoming(15)
        return templates.TemplateResponse(
            request,
            "categories.html",
            {"categories": cats, "config": cfg, "calendar": cal},
        )

    @app.get("/api/categories")
    def api_categories():
        return load_category_config()

    @app.post("/api/categories")
    async def api_categories_update(request: Request):
        body = await request.json()
        save_category_config(body)
        return JSONResponse({"ok": True})

    @app.get("/videos/{video_id}")
    def video_detail(video_id: int):
        with session_scope() as session:
            asset = session.get(VideoAsset, video_id)
            if not asset:
                raise HTTPException(404)
            snaps = list(
                session.scalars(
                    select(VideoPerformanceSnapshot)
                    .where(VideoPerformanceSnapshot.video_asset_id == video_id)
                    .order_by(VideoPerformanceSnapshot.collected_at)
                )
            )
            mistakes = list(
                session.scalars(
                    select(MistakeReport).where(MistakeReport.video_asset_id == video_id)
                )
            )
        perf = PerformanceAnalyzer.summarize([{"metrics": s.metrics} for s in snaps])
        return {
            "asset": {
                "id": asset.id,
                "path": asset.local_path,
                "qc": asset.qc_report,
            },
            "performance": perf,
            "mistakes": [m.report_json for m in mistakes],
        }

    return app
