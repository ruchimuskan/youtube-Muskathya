from __future__ import annotations

import json
import re
from typing import Any


def _strip_markdown_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```\s*$", "", text)
    return text.strip()


def _extract_json_object(text: str) -> str | None:
    """Return the outermost {...} substring if present."""
    text = _strip_markdown_fence(text)
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def _close_truncated_json(fragment: str) -> str:
    """Best-effort repair when the model output was cut mid-string."""
    s = fragment.rstrip()
    if s.endswith("}"):
        return s
    in_string = False
    escape = False
    for ch in s:
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
        elif ch == '"':
            in_string = True
    if in_string:
        s += '"'
    open_braces = s.count("{") - s.count("}")
    open_brackets = s.count("[") - s.count("]")
    s += "]" * max(open_brackets, 0)
    s += "}" * max(open_braces, 0)
    return s


def parse_json_object(text: str) -> dict[str, Any]:
    text = _strip_markdown_fence(text)
    candidates = [text]
    extracted = _extract_json_object(text)
    if extracted and extracted != text:
        candidates.insert(0, extracted)
    if extracted:
        candidates.append(_close_truncated_json(extracted))
    else:
        start = text.find("{")
        if start >= 0:
            candidates.append(_close_truncated_json(text[start:]))

    last_error: json.JSONDecodeError | None = None
    for candidate in candidates:
        try:
            data = json.loads(candidate)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError as exc:
            last_error = exc
            continue
    if last_error:
        raise last_error
    raise ValueError("No JSON object found in model output")
