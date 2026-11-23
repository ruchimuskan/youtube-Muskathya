from pathlib import Path
from unittest.mock import MagicMock, patch
from app.youtube.upload_dispatch import dispatch_youtube_upload
from app.youtube.upload_queue import _load


def test_upload_dispatch_falls_back_to_queue_on_auth_failure(tmp_path: Path):
    video_file = tmp_path / "test_video.mp4"
    video_file.write_bytes(b"dummy_video_bytes")
    thumb_file = tmp_path / "test_thumb.png"
    thumb_file.write_bytes(b"dummy_thumb_bytes")

    metadata = {
        "title": "परीक्षण वीडियो",
        "description": "परीक्षण विवरण",
        "tags": ["परीक्षण"],
        "category_id": "24",
    }

    with patch("app.youtube.upload_dispatch.can_upload_today", return_value=True):
        with patch("app.youtube.upload_dispatch.YouTubeUploader") as mock_uploader_cls:
            mock_uploader = MagicMock()
            mock_uploader.upload_video.side_effect = RuntimeError(
                "YouTube OAuth token expired or revoked: invalid_grant"
            )
            mock_uploader_cls.return_value = mock_uploader

            result = dispatch_youtube_upload(
                video_asset_id=999,
                video_path=video_file,
                thumbnail_path=thumb_file,
                metadata=metadata,
                story_id=123,
            )

            assert result["status"] == "queued"
            assert "error" in result
            assert "invalid_grant" in result["error"]
            assert "queue_id" in result
