import pytest
from unittest.mock import MagicMock, patch
import httpx

from app.ai.providers.cloudflare import CloudflareWorkersAI
from app.ai.providers.router import LLMRouter


def test_cloudflare_fallback_on_429():
    provider = CloudflareWorkersAI()
    provider.settings.cloudflare_account_id = "test_acc"
    provider.settings.cloudflare_api_token = "test_token"
    provider.settings.cloudflare_model = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"

    resp_429 = MagicMock()
    resp_429.status_code = 429
    resp_429.text = "Too Many Requests"

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


def test_cloudflare_non_llama_strips_response_format():
    provider = CloudflareWorkersAI()
    provider.settings.cloudflare_account_id = "test_acc"
    provider.settings.cloudflare_api_token = "test_token"
    provider.settings.cloudflare_model = "@cf/mistral/mistral-7b-instruct-v0.2"

    resp_200 = MagicMock()
    resp_200.status_code = 200
    resp_200.json.return_value = {"result": {"response": '{"test": 1}'}, "success": True}
    resp_200.raise_for_status.return_value = None

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.post.return_value = resp_200
        mock_client_cls.return_value = mock_client

        res = provider.complete("कहानी लिखो", json_mode=True)
        assert res.text == '{"test": 1}'
        call_kwargs = mock_client.post.call_args[1]
        assert "response_format" not in call_kwargs["json"]


def test_router_gemini_fallback():
    router = LLMRouter()
    router._cloudflare = MagicMock()
    router._cloudflare.name = "cloudflare"
    router._cloudflare.settings.cloudflare_model = "test-model"
    router._cloudflare.is_available.return_value = True
    router._cloudflare.complete.side_effect = RuntimeError("All Cloudflare models 429 rate limited")

    router._gemini = MagicMock()
    router._gemini.name = "gemini"
    router._gemini.is_available.return_value = True
    from app.ai.providers.base import LLMResponse
    router._gemini.complete.return_value = LLMResponse(text="कहानी फ्रॉम जेमिनी", provider="gemini", model="gemini-2.0-flash")

    res = router.complete("कहानी लिखो")
    assert res.provider == "gemini"
    assert res.text == "कहानी फ्रॉम जेमिनी"


def test_story_generator_fallback_when_llm_fails():
    from app.ai.story_generator import StoryGenerator, StoryGenerationRequest

    mock_llm = MagicMock()
    mock_llm.complete.side_effect = RuntimeError("All Cloudflare models 429 rate limited")

    gen = StoryGenerator(llm=mock_llm)
    req = StoryGenerationRequest(
        language="hi",
        genre="horror_mystery",
        target_duration_sec=360,
        is_short=False,
        category_id="horror_mystery",
    )
    story = gen.generate(req)
    assert story is not None
    assert len(story["scenes"]) >= 8
    assert "रहस्य" in story["title"]
    assert len(story["characters"]) == 2
    for sc in story["scenes"]:
        assert len(sc["narration"]) > 100
        assert len(sc["dialogue"]) >= 1


def test_cloudflare_flux_payload(tmp_path):
    from app.images.cloudflare_image import CloudflareImageGenerator
    gen = CloudflareImageGenerator()
    gen.settings.cloudflare_account_id = "test_acc"
    gen.settings.cloudflare_api_token = "test_tok"
    gen.settings.cloudflare_image_model = "@cf/black-forest-labs/flux-1-schnell"

    resp_200 = MagicMock()
    resp_200.status_code = 200
    resp_200.headers = {"content-type": "application/json"}
    # 1000x600 test png with color variance
    from io import BytesIO
    from PIL import Image, ImageDraw
    test_img = Image.new("RGB", (1000, 600), color=(50, 50, 50))
    draw = ImageDraw.Draw(test_img)
    draw.rectangle([100, 100, 500, 500], fill=(240, 180, 40))
    draw.line([0, 0, 1000, 600], fill=(255, 0, 0), width=10)
    buf = BytesIO()
    test_img.save(buf, format="PNG")
    import base64
    b64_data = base64.b64encode(buf.getvalue()).decode("utf-8")
    resp_200.json.return_value = {"result": {"image": b64_data}, "success": True}
    resp_200.raise_for_status.return_value = None

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.post.return_value = resp_200
        mock_client_cls.return_value = mock_client

        out_file = tmp_path / "test_flux.png"
        res_path = gen.generate("cinematic scene", out_file, (1280, 720))

        assert res_path.exists()
        call_kwargs = mock_client.post.call_args[1]
        payload = call_kwargs["json"]
        assert payload["prompt"] == "cinematic scene"
        assert "steps" in payload
        # Ensure rejected params are NOT sent to flux
        assert "width" not in payload
        assert "height" not in payload
        assert "negative_prompt" not in payload

