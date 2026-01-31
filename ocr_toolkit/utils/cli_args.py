"""
CLI argument utilities.

This module provides utilities for adding common command-line arguments
to argparse parsers across different CLI commands.
"""

import argparse

from .. import config


def add_common_ocr_args(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """
    Add common OCR-related command-line arguments to an argparse parser.

    This function adds standard OCR processing arguments that are used
    across multiple CLI commands in the toolkit.

    Args:
        parser: The argument parser to add arguments to

    Returns:
        The parser with added arguments
    """
    parser.add_argument(
        "--cpu",
        action="store_true",
        help="Force use of CPU even if GPU is available"
    )
    parser.add_argument(
        "--pages",
        type=str,
        default=None,
        help="Process only selected pages, e.g. '1-30' or '1-5,10,20-25'"
    )
    parser.add_argument(
        "--profile",
        action="store_true",
        help="Print fine-grained timing (startup, load, per-page, totals)"
    )
    return parser



def add_output_args(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """
    Add common output-related arguments to an argparse parser.

    Args:
        parser: The argument parser to add arguments to

    Returns:
        The parser with added arguments
    """
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help=f"Output directory for files (default: '{config.DEFAULT_MARKDOWN_OUTPUT_DIR}' in input directory)"
    )
    parser.add_argument(
        "--preserve-structure", "-p",
        action="store_true",
        help="Preserve original directory structure in output (when processing directories)"
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Disable recursive search in directories (process only top-level files)"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Reduce output verbosity"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Increase output verbosity"
    )
    return parser
