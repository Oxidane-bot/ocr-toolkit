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
        "--batch-size",
        type=int,
        default=config.DEFAULT_BATCH_SIZE,
        help="Number of pages to process at a time"
    )
    parser.add_argument(
        "--cpu", 
        action="store_true", 
        help="Force use of CPU even if CUDA is available"
    )
    parser.add_argument(
        "--det-arch",
        type=str,
        default=config.DEFAULT_DET_ARCH,
        help="Detection model architecture to use"
    )
    parser.add_argument(
        "--reco-arch",
        type=str,
        default=config.DEFAULT_RECO_ARCH,
        help="Recognition model architecture to use"
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