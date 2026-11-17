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
    """Normalize for TTS without removing meaningful words, eliminating all stutter/loop triggers."""
    if not text:
        return ""
    t = unicodedata.normalize("NFC", text)
    t = t.replace("\u200c", "").replace("\u200d", "")  # ZWNJ/ZWJ
    t = t.replace("…", "।")
    # Replace multiple dots (e.g. '...', '..') with single Purna Viram '।'
    t = re.sub(r"\.{2,}", "।", t)
    # Remove smart quotes and plain quotes
    t = t.replace("“", "").replace("”", "").replace('"', "")
    t = t.replace("‘", "").replace("’", "").replace("'", "")
    t = t.replace("`", "")
    # Remove brackets and symbols that cause espeak-ng/piper phonemizer loops
    t = re.sub(r"[\[\]\(\)\{\}<>/\\]", " ", t)
    t = re.sub(r"[\-—–_~*#@$^&=+]", " ", t)
    # Replace colons, semicolons with Purna Viram
    t = re.sub(r"[:;]", "।", t)
    # Clean mixed or repeated punctuation (e.g., '..?', '??', '!!', '।।')
    t = re.sub(r"[!?\.]*\?+[!?\.]*", "? ", t)
    t = re.sub(r"[!\.]*!+[!\.]*", "! ", t)
    t = re.sub(r"[।\.]+[।\.]*", "। ", t)
    # Space out commas cleanly
    t = re.sub(r"\s*([,،])\s*", r"\1 ", t)
    t = re.sub(r"[ \t]+", " ", t)
    return t.strip()


def split_hindi_for_tts(text: str) -> list[str]:
    """
    Split into short clauses for reliable Piper Hindi synthesis.
    Preserves all words — never drops prefixes.
    Ensures clauses are not micro-stubs that cause VITS duration prediction glitches.
    """
    t = normalize_hindi_text(text)
    if not t:
        return []

    chunks: list[str] = []
    # Split by major sentence terminators
    for sentence in re.split(r"(?<=[।!?])\s+", t):
        sentence = sentence.strip()
        if not sentence:
            continue
        # Split on comma if both sides have at least 2 words to prevent 1-syllable VITS glitch
        if ("," in sentence or "،" in sentence) and len(sentence.split()) >= 4:
            parts = re.split(r"\s*[,،]\s*", sentence)
            merged_parts: list[str] = []
            cur = ""
            for p in parts:
                p = p.strip()
                if not p:
                    continue
                if cur and (len(cur.split()) < 2 or len(p.split()) < 2):
                    cur = cur + " " + p
                else:
                    if cur:
                        merged_parts.append(cur)
                    cur = p
            if cur:
                merged_parts.append(cur)

            for part in merged_parts:
                part = part.strip()
                if not part:
                    continue
                if not re.search(r"[।!?]$", part):
                    part = part + "। "
                chunks.append(part.strip())
        else:
            chunks.append(sentence)

    # Clean every chunk so no trailing dots or dashes exist
    clean_chunks = []
    for c in chunks:
        c = c.strip()
        if not c:
            continue
        if not re.search(r"[।!?]$", c):
            c = c + "।"
        clean_chunks.append(c)

    return clean_chunks


def prepare_hindi_tts(text: str) -> HindiTTSInput:
    original = text or ""
    normalized = normalize_hindi_text(original)
    segments = split_hindi_for_tts(normalized)
    if not segments and normalized:
        segments = [normalized]
    return HindiTTSInput(original=original, normalized=normalized, segments=segments)


def devanagari_char_count(text: str) -> int:
    return sum(1 for ch in text if "\u0900" <= ch <= "\u097f")
