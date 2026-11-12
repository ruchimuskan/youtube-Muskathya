from __future__ import annotations

import re


def split_subtitle_chunks(text: str, *, max_chars: int = 42, max_lines: int = 2) -> list[str]:
    """Break Hindi/any text into readable subtitle cues (1–2 lines)."""
    text = re.sub(r"\s+", " ", (text or "").strip())
    if not text:
        return []

    sentences = re.split(r"(?<=[।!?\.])\s+", text)
    chunks: list[str] = []

    for sentence in sentences:
        words = sentence.split()
        line = ""
        block_lines: list[str] = []
        for word in words:
            candidate = f"{line} {word}".strip() if line else word
            if len(candidate) <= max_chars:
                line = candidate
            else:
                if line:
                    block_lines.append(line)
                line = word
                if len(block_lines) >= max_lines:
                    chunks.append("\n".join(block_lines[:max_lines]))
                    block_lines = []
        if line:
            block_lines.append(line)
        if block_lines:
            chunks.append("\n".join(block_lines[:max_lines]))

    return chunks if chunks else [text[: max_chars * max_lines]]
