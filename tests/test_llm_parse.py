from app.ai.providers.router import LLMRouter


def test_parse_json_strips_fence():
    text = '```json\n{"a": 1}\n```'
    assert LLMRouter.parse_json(text) == {"a": 1}


def test_parse_json_nested():
    assert LLMRouter.parse_json('prefix {"ok": true}') == {"ok": True}
