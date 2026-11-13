from app.creative.hindi_thumbnail_copy import (
    SHIVA_GANESHA_HEADLINE,
    SHIVA_GANESHA_SUSPENSE,
    resolve_overlay_text,
    sanitize_hindi,
)


def test_shiva_ganesha_locked_copy():
    story = {"title": "शिव जी के गणेश को दिया गया उपहार", "characters": [{"name": "शिव जी"}, {"name": "गणेश"}]}
    h, s, locked = resolve_overlay_text(story, "mythology_inspired", {})
    assert locked
    assert h == SHIVA_GANESHA_HEADLINE
    assert s == SHIVA_GANESHA_SUSPENSE
    assert "**" not in h


def test_sanitize_strips_markdown():
    assert sanitize_hindi("**शिव जी**") == "शिव जी"
