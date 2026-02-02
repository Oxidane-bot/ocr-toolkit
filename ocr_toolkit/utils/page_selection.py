"""
Page selection parsing utilities.

This module parses the CLI `--pages` argument used to select a subset of pages
to process, e.g. "1-5,10,20-25".
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ParsedPages:
    """Parsed page selection, 0-based indices in ascending order."""

    indices: list[int]


def parse_pages_arg(pages: str | None) -> ParsedPages | None:
    """
    Parse a `--pages` argument string into 0-based page indices.

    Supported formats:
    - "1"
    - "1-5"
    - "1-5,10,20-25"

    Args:
        pages: Raw pages argument or None.

    Returns:
        ParsedPages or None if pages is None/empty.
    """
    if pages is None:
        return None

    raw = str(pages).strip()
    if not raw:
        return None

    raw = raw.replace(" ", "")
    indices: set[int] = set()

    for part in raw.split(","):
        if not part:
            continue

        if "-" in part:
            start_s, end_s = part.split("-", 1)
            if not start_s or not end_s:
                raise ValueError(f"Invalid --pages range: '{part}'")

            start = int(start_s)
            end = int(end_s)
            if start <= 0 or end <= 0:
                raise ValueError("Page numbers must be >= 1")

            lo, hi = (start, end) if start <= end else (end, start)
            for page in range(lo, hi + 1):
                indices.add(page - 1)
        else:
            page = int(part)
            if page <= 0:
                raise ValueError("Page numbers must be >= 1")
            indices.add(page - 1)

    return ParsedPages(indices=sorted(indices))
