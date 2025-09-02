#!/usr/bin/env python3
"""
Slice the first N pages from a PDF and write to a new PDF.

Usage:
  python scripts/slice_pdf_first_pages.py INPUT_PDF OUTPUT_PDF [N]

Defaults to N=30 if not provided.
"""

import sys
import os
from typing import Optional

DEFAULT_N = 30


def slice_pdf(input_path: str, output_path: str, num_pages: int = DEFAULT_N) -> None:
    try:
        from pypdf import PdfReader, PdfWriter
    except Exception as e:
        print("pypdf is required. Install with: uv run python -m pip install pypdf", file=sys.stderr)
        raise

    reader = PdfReader(input_path)
    writer = PdfWriter()

    total = len(reader.pages)
    end = min(num_pages, total)

    for i in range(end):
        writer.add_page(reader.pages[i])

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "wb") as f:
        writer.write(f)

    print(f"Wrote first {end} pages (of {total}) to: {output_path}")


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("Usage: python scripts/slice_pdf_first_pages.py INPUT_PDF OUTPUT_PDF [N]", file=sys.stderr)
        return 2
    input_pdf = argv[1]
    output_pdf = argv[2]
    n = int(argv[3]) if len(argv) >= 4 else DEFAULT_N

    if not os.path.exists(input_pdf):
        print(f"Input not found: {input_pdf}", file=sys.stderr)
        return 1

    slice_pdf(input_pdf, output_pdf, n)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv)) 