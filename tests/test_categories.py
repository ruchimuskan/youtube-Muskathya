from app.content.categories import CATEGORIES, get_category, format_duration_range
from app.content.category_config import load_category_config


def test_all_categories_have_weights():
    cfg = load_category_config()
    for cid in cfg.get("enabled_categories", []):
        assert cid in CATEGORIES


def test_format_duration_long():
    lo, hi, min_s, max_s = format_duration_range("long")
    assert 300 <= lo <= 400
    assert min_s < max_s


def test_get_category_default():
    c = get_category("unknown_id")
    assert c.id == "moral"
