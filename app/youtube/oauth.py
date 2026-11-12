from __future__ import annotations

import json
import logging
import os
import re
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from app.config import get_settings

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]

_STATE_RE = re.compile(r"^[A-Za-z0-9_\-]+$")


def _configure_oauthlib_for_local_dev(redirect_uri: str) -> None:
    """Allow http://127.0.0.1 callbacks during local dev (never use in production)."""
    if redirect_uri.startswith("http://"):
        os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")
    os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")


class YouTubeOAuth:
    def __init__(self) -> None:
        self.settings = get_settings()
        _configure_oauthlib_for_local_dev(self.settings.google_redirect_uri)

    def _token_path(self) -> Path:
        return self.settings.youtube_oauth_token_file

    def _pending_dir(self) -> Path:
        path = self.settings.data_dir / "oauth_pending"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _secure_file(self, path: Path) -> None:
        if path.exists():
            os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)

    def get_flow(self, *, state: str | None = None, code_verifier: str | None = None) -> Flow:
        if not self.settings.google_client_secrets_file.exists():
            raise FileNotFoundError(
                f"Missing OAuth client secrets: {self.settings.google_client_secrets_file}"
            )
        kwargs: dict[str, Any] = {
            "redirect_uri": self.settings.google_redirect_uri,
        }
        if state:
            kwargs["state"] = state
        if code_verifier:
            kwargs["code_verifier"] = code_verifier
            kwargs["autogenerate_code_verifier"] = False
        return Flow.from_client_secrets_file(
            str(self.settings.google_client_secrets_file),
            scopes=SCOPES,
            **kwargs,
        )

    def _pending_path(self, state: str) -> Path:
        if not _STATE_RE.match(state):
            raise ValueError("Invalid OAuth state")
        return self._pending_dir() / f"{state}.json"

    def _save_pending_pkce(self, state: str, code_verifier: str) -> None:
        path = self._pending_path(state)
        path.write_text(
            json.dumps(
                {
                    "code_verifier": code_verifier,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            ),
            encoding="utf-8",
        )
        self._secure_file(path)

    def _load_pending_pkce(self, state: str) -> str:
        path = self._pending_path(state)
        if not path.exists():
            raise FileNotFoundError(
                "OAuth session not found or expired. Click Connect YouTube again (do not refresh the callback page)."
            )
        data = json.loads(path.read_text(encoding="utf-8"))
        verifier = data.get("code_verifier")
        if not verifier:
            raise ValueError("Invalid pending OAuth data")
        return str(verifier)

    def start_authorization(self) -> str:
        """Begin OAuth; persists PKCE verifier until callback completes."""
        flow = self.get_flow()
        url, state = flow.authorization_url(
            access_type="offline",
            prompt="consent",
        )
        if not flow.code_verifier:
            raise RuntimeError("OAuth PKCE code_verifier was not generated")
        self._save_pending_pkce(state, flow.code_verifier)
        return url

    def authorization_url(self) -> tuple[str, str]:
        flow = self.get_flow()
        url, state = flow.authorization_url(
            access_type="offline",
            prompt="consent",
        )
        if flow.code_verifier:
            self._save_pending_pkce(state, flow.code_verifier)
        return url, state

    def complete_authorization(self, state: str, authorization_response: str) -> Credentials:
        path = self._pending_path(state)
        code_verifier = self._load_pending_pkce(state)
        flow = self.get_flow(state=state, code_verifier=code_verifier)
        try:
            flow.fetch_token(authorization_response=authorization_response)
        finally:
            path.unlink(missing_ok=True)

        creds = flow.credentials
        self.save_credentials(creds)
        return creds

    def exchange_code(self, code: str, state: str | None = None) -> Credentials:
        if not state:
            raise ValueError("Missing OAuth state")
        redirect = f"{self.settings.google_redirect_uri}?code={code}&state={state}"
        return self.complete_authorization(state, redirect)

    def save_credentials(self, creds: Credentials) -> None:
        path = self._token_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": list(creds.scopes or SCOPES),
            "expiry": creds.expiry.isoformat() if creds.expiry else None,
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self._secure_file(path)

    def load_credentials(self) -> Credentials | None:
        path = self._token_path()
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        creds = Credentials(
            token=data.get("token"),
            refresh_token=data.get("refresh_token"),
            token_uri=data.get("token_uri"),
            client_id=data.get("client_id"),
            client_secret=data.get("client_secret"),
            scopes=data.get("scopes"),
        )
        if data.get("expiry"):
            creds.expiry = datetime.fromisoformat(data["expiry"])
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            self.save_credentials(creds)
        return creds

    def connection_status(self) -> dict[str, Any]:
        creds = self.load_credentials()
        if not creds:
            return {"connected": False, "message": "Not authorized"}
        expired = bool(creds.expired)
        return {
            "connected": True,
            "expired": expired,
            "scopes": list(creds.scopes or []),
        }
