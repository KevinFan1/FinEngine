"""Live-code extraction helpers."""

from __future__ import annotations

import re

LIVE_CODE_PATTERN = re.compile(r"[A-Za-z]+\d+(?:-[FMfm])?")


def extract_live_code(value: object) -> str:
    """Extract the normalized live code from a raw purchase live-code cell."""
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    match = LIVE_CODE_PATTERN.search(text)
    return match.group(0).upper() if match else ""
