from app.content.categories import CATEGORIES, get_category, format_duration_range
from app.content.category_config import load_category_config


def test_all_categories_have_weights():
    cfg = load_category_config()
    for cid in cfg.get("enabled_categories", []):
        assert cid in CATEGORIES


def test_format_duration_long():
    lo, hi, min_s, max_s = format_duration_range("long")
    assert 600 <= lo <= 700
    assert min_s < max_s


def test_get_category_default():
    c = get_category("unknown_id")
    assert c.id == "moral"


def test_story_generator_has_retention_rules():
    from app.ai.story_generator import StoryGenerator
    from app.content.categories import category_story_block

    gen = StoryGenerator()
    sys_prompt = gen._hindi_system()
    assert "NO BORING STORIES" in sys_prompt
    assert "COLD OPEN HOOK" in sys_prompt
    assert "NATURAL HINDI DIALOGUES" in sys_prompt

    block = category_story_block(get_category("suspense_thriller"))
    assert "HIGH RETENTION DIRECTIVE" in block
