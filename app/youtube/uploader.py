from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from app.config import get_settings
from app.database import Repository, session_scope
from app.database.models import VideoPrivacy, YouTubeUpload
from app.youtube.oauth import YouTubeOAuth

logger = logging.getLogger(__name__)


class YouTubeUploader:
    def __init__(self, oauth: YouTubeOAuth | None = None) -> None:
        self.oauth = oauth or YouTubeOAuth()
        self.settings = get_settings()

    def _youtube(self):
        creds = self.oauth.load_credentials()
        if not creds:
            raise RuntimeError("YouTube OAuth required")
        return build("youtube", "v3", credentials=creds)

    def upload_video(
        self,
        video_asset_id: int,
        file_path: Path,
        metadata: dict[str, Any],
        *,
        privacy: str | None = None,
        publish_at: datetime | None = None,
        thumbnail_path: Path | None = None,
    ) -> dict[str, Any]:
        privacy = privacy or self.settings.privacy_mode
        if self.settings.emergency_stop:
            raise RuntimeError("Emergency stop is enabled")

        with session_scope() as session:
            if Repository(session).uploads_today_count() >= self.settings.max_daily_uploads:
                raise RuntimeError("Maximum daily uploads reached")

        youtube = self._youtube()
        body: dict[str, Any] = {
            "snippet": {
                "title": metadata["title"][:100],
                "description": metadata.get("description", ""),
                "tags": metadata.get("tags", [])[:500],
                "categoryId": str(metadata.get("category_id", "24")),
            },
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": False,
            },
        }
        if publish_at and privacy != "private":
            body["status"]["publishAt"] = publish_at.isoformat().replace("+00:00", "Z")
            body["status"]["privacyStatus"] = "private"  # required until publish time

        media = MediaFileUpload(
            str(file_path),
            chunksize=self.settings.youtube_upload_chunk_size,
            resumable=True,
            mimetype="video/*",
        )

        request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
        response = None
        errors: list[str] = []
        try:
            while response is None:
                status, response = request.next_chunk()
                if status:
                    logger.info("Upload progress: %.1f%%", status.progress() * 100)
        except HttpError as exc:
            errors.append(str(exc))
            raise

        video_id = response["id"]
        url = f"https://www.youtube.com/watch?v={video_id}"

        thumb_status = "skipped"
        if thumbnail_path and thumbnail_path.exists():
            try:
                tmedia = MediaFileUpload(str(thumbnail_path), mimetype="image/jpeg")
                youtube.thumbnails().set(videoId=video_id, media_body=tmedia).execute()
                thumb_status = "uploaded"
            except HttpError as exc:
                thumb_status = "failed"
                errors.append(f"thumbnail: {exc}")

        with session_scope() as session:
            row = YouTubeUpload(
                video_asset_id=video_asset_id,
                youtube_video_id=video_id,
                youtube_url=url,
                title=metadata["title"][:100],
                description=metadata.get("description", ""),
                tags=metadata.get("tags", []),
                category_id=str(metadata.get("category_id", "24")),
                privacy=VideoPrivacy(privacy),
                scheduled_publish_at=publish_at,
                upload_status="completed",
                thumbnail_status=thumb_status,
                api_errors={"errors": errors} if errors else None,
                uploaded_at=datetime.utcnow(),
            )
            session.add(row)
            session.flush()
            upload_id = row.id
            Repository(session).audit(
                "video_uploaded", "youtube_upload", str(upload_id), {"video_id": video_id}
            )

        return {
            "id": upload_id,
            "youtube_video_id": video_id,
            "youtube_url": url,
            "thumbnail_status": thumb_status,
            "api_errors": errors or None,
        }
