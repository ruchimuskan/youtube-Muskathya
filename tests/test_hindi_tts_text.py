from app.voice.hindi_text import prepare_hindi_tts, split_hindi_for_tts


def test_comma_splits_without_dropping_words():
    text = "रोहित की माँ ने कहा, यहाँ आओ।"
    prep = prepare_hindi_tts(text)
    joined = " ".join(prep.segments)
    assert "रोहित" in joined
    assert "माँ" in joined
    assert "यहाँ" in joined
    assert len(prep.segments) >= 2


def test_two_sentences():
    text = "रोहित की माँ ने कहा, यहाँ आओ। रोहित ने पूछा, क्या हुआ माँ?"
    segs = split_hindi_for_tts(text)
    assert len(segs) >= 3
    assert any("रोहित की" in s for s in segs)
