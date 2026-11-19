import pytest
from unittest.mock import MagicMock, patch
import httpx

from app.ai.providers.cloudflare import CloudflareWorkersAI


def test_cloudflare_fallback_on_429():
    provider = CloudflareWorkersAI()
    provider.settings.cloudflare_account_id = "test_acc"
    provider.settings.cloudflare_api_token = "test_token"
    provider.settings.cloudflare_model = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"

    # Mock responses: first call returns 429, second call with fallback model returns 200
    resp_429 = MagicMock()
    resp_429.status_code = 429

    resp_200 = MagicMock()
    resp_200.status_code = 200
    resp_200.json.return_value = {"result": {"response": "नमस्ते यह कहानी है।"}, "success": True}
    resp_200.raise_for_status.return_value = None

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.post.side_effect = [resp_429, resp_200]
        mock_client_cls.return_value = mock_client

        res = provider.complete("कहानी लिखो", system="सिस्टम")
        assert res.text == "नमस्ते यह कहानी है।"
        assert res.model == "@cf/meta/llama-3.1-8b-instruct"
        assert mock_client.post.call_count == 2
