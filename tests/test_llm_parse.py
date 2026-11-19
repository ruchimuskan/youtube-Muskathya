from unittest.mock import MagicMock

from app.ai.providers.router import LLMRouter
from app.ai.seo_generator import SEOGenerator


def test_parse_json_strips_fence():
    text = '```json\n{"a": 1}\n```'
    assert LLMRouter.parse_json(text) == {"a": 1}


def test_parse_json_nested():
    assert LLMRouter.parse_json('prefix {"ok": true}') == {"ok": True}


def test_seo_generator_fallback_on_llm_failure():
    mock_llm = MagicMock()
    mock_llm.complete.side_effect = RuntimeError("Rate limit or connection error")
    generator = SEOGenerator(llm=mock_llm)
    seo = generator.generate({"title": "परीक्षा का दिन", "synopsis": "एक छात्र की कहानी"}, "hi")
    assert "परीक्षा का दिन" in seo["recommended_title"]
    assert len(seo["tags"]) > 0
    assert seo["category_id"] == "24"
