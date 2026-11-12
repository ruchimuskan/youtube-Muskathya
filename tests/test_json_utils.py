import pytest

from app.ai.json_utils import parse_json_object


def test_parse_wrapped_json():
    assert parse_json_object('```json\n{"a": 1}\n```') == {"a": 1}


def test_parse_embedded_json():
    text = 'Here is data {"title": "x", "n": 2} thanks'
    assert parse_json_object(text)["title"] == "x"

