from app.utils.hindi_text import split_subtitle_chunks


def test_split_subtitle_chunks():
    text = "यह एक लंबी कहानी है। दूसरा वाक्य यहाँ है।"
    parts = split_subtitle_chunks(text, max_chars=20, max_lines=2)
    assert len(parts) >= 1
    assert all(len(p) <= 45 for p in parts)
