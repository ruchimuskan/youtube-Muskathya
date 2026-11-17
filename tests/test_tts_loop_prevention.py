import pytest
from pathlib import Path
from app.voice.hindi_text import normalize_hindi_text, split_hindi_for_tts
from app.voice.tts_verify import max_duration_for_text, min_duration_for_text, verify_segment


def test_normalize_hindi_text_strips_loop_triggers():
    # Ellipses, multiple dots, repeated questions, dashes
    raw = 'रोहन ने कहा... "तुम क्या कर रहे हो???" — यह सब क्या है...?'
    clean = normalize_hindi_text(raw)

    # Must not contain quotes, multiple dots, dashes, or repeated punctuation
    assert '...' not in clean
    assert '..' not in clean
    assert '??' not in clean
    assert '"' not in clean
    assert '—' not in clean
    assert '-' not in clean
    assert '?' in clean
    assert '।' in clean


def test_split_hindi_for_tts_cleans_clauses():
    raw = "पापा...? यह कैसे संभव है... मुझे मत मारो!"
    chunks = split_hindi_for_tts(raw)

    for c in chunks:
        assert '...' not in c
        assert '..' not in c
        assert c.endswith('।') or c.endswith('?') or c.endswith('!')


def test_tts_verify_flags_looping_audio(tmp_path):
    wav = tmp_path / "test_loop.wav"
    wav.write_bytes(b"\x00" * 44100 * 2 * 60)  # 60s of dummy data

    # 10 character text: expected ~1-2s, max ~4-5s
    res = verify_segment("तुम क्या कर रहे हो?", wav, duration_sec=60.0)
    assert not res.passed
    assert any("VITS loop" in note or "abnormally long" in note for note in res.notes)
