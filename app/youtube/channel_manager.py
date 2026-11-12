from __future__ import annotations

import logging

from googleapiclient.discovery import build

from app.database import Repository, session_scope
from app.youtube.oauth import YouTubeOAuth

logger = logging.getLogger(__name__)


class ChannelManager:
    def __init__(self, oauth: YouTubeOAuth | None = None) -> None:
        self.oauth = oauth or YouTubeOAuth()

    def verify_and_save_channel(self) -> dict:
        creds = self.oauth.load_credentials()
        if not creds:
            raise RuntimeError("YouTube not connected. Run OAuth first.")

        youtube = build("youtube", "v3", credentials=creds)
        resp = youtube.channels().list(part="snippet", mine=True).execute()
        items = resp.get("items", [])
        if not items:
            raise RuntimeError("No channel found for authenticated account.")

        ch = items[0]
        channel_id = ch["id"]
        title = ch["snippet"]["title"]

        with session_scope() as session:
            repo = Repository(session)
            repo.save_channel(channel_id, title)
            repo.audit("channel_verified", "channel", channel_id, {"title": title})

        return {"channel_id": channel_id, "channel_title": title, "verified": True}
