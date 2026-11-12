from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


@dataclass
class HindiTTSInput:
    original: str
    normalized: str
    segments: list[str]


def normalize_hindi_text(text: str) -> str:
    """Normalize for TTS without removing meaningful words."""
    if not text:
        return ""
    t = unicodedata.normalize("NFC", text)
    t = t.replace("\u200c", "").replace("\u200d", "")  # ZWNJ/ZWJ
    t = t.replace(""", '"').replace(""", '"')
    t = t.replace("'", "'").replace("'", "'")
    t = t.replace("…", "।")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\s*([,،])\s*", r"\1 ", t)
    return t.strip()


def split_hindi_for_tts(text: str) -> list[str]:
    """
    Split into short clauses for reliable Piper Hindi synthesis.
    Preserves all words — never drops prefixes.
    """
    t = normalize_hindi_text(text)
    if not t:
        return []

    chunks: list[str] = []
    for sentence in re.split(r"(?<=[।!?\.])\s+", t):
        sentence = sentence.strip()
        if not sentence:
            continue
        if "," in sentence or "،" in sentence:
            parts = re.split(r"\s*[,،]\s*", sentence)
            for i, part in enumerate(parts):
                part = part.strip()
                if not part:
                    continue
                if not re.search(r"[।!?\.]$", part):
                    part = part + "।"
                chunks.append(part)
        else:
            chunks.append(sentence)

    return [c for c in chunks if c.strip()]


def prepare_hindi_tts(text: str) -> HindiTTSInput:
    original = text or ""
    normalized = normalize_hindi_text(original)
    segments = split_hindi_for_tts(normalized)
    if not segments and normalized:
        segments = [normalized]
    return HindiTTSInput(original=original, normalized=normalized, segments=segments)


def devanagari_char_count(text: str) -> int:
    return sum(1 for ch in text if "\u0900" <= ch <= "\u097f")
