"""
Configuration module for OCR toolkit.

This module contains default configuration values used across the OCR toolkit,
including processing parameters, output directories, and supported file formats.

For PaddleOCR-VL, models are managed internally by the library.
"""

# Default processing parameters
DEFAULT_BATCH_SIZE = 1
"""int: Default batch size for processing pages.

This value determines how many pages are processed simultaneously.
Larger values may improve throughput but require more memory.
"""

DEFAULT_WORKERS = 4
"""int: Default number of concurrent workers for batch processing."""

# Display and UI constants
MAX_TREE_DISPLAY_SMALL = 10
"""int: Maximum files to show in tree view for small file counts."""

MAX_TREE_DISPLAY_MEDIUM = 20
"""int: Maximum files to show in tree view for medium file counts."""

MAX_TREE_DISPLAY_LARGE = 25
"""int: Maximum files to show when user explicitly requests full display."""

# Quality evaluation thresholds
QUALITY_SPECIAL_CHAR_THRESHOLD = 0.05
"""float: Maximum ratio of special characters (5%) before quality penalty."""

QUALITY_SHORT_WORD_THRESHOLD = 0.3
"""float: Maximum ratio of very short words (30%) before quality penalty."""

# Path and encoding constants
ASCII_BOUNDARY = 127
"""int: Character code boundary for ASCII/non-ASCII detection."""

MAX_RELATIVE_PATH_LENGTH = 200
"""int: Maximum safe relative path length (Windows has 260 char limit)."""

# Default output subdirectory names
DEFAULT_MARKDOWN_OUTPUT_DIR = "markdown_output"
"""str: Default subdirectory name for markdown output files."""

DEFAULT_OCR_OUTPUT_DIR = "output_ocr"
"""str: Default subdirectory name for OCR-processed PDF files."""

# Supported file formats (centralized)
SUPPORTED_PDF_FORMATS = {".pdf"}
"""Set[str]: PDF file formats supported by the toolkit."""

SUPPORTED_IMAGE_FORMATS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".gif"}
"""Set[str]: Image file formats supported by OCR processing."""

SUPPORTED_OFFICE_FORMATS = {".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx"}
"""Set[str]: Office document formats that can be converted to PDF for OCR."""

SUPPORTED_TEXT_FORMATS = {".txt", ".md", ".html", ".htm", ".rtf"}
"""Set[str]: Text document formats supported by MarkItDown."""

SUPPORTED_OPENDOC_FORMATS = {".odt", ".odp", ".ods"}
"""Set[str]: OpenDocument formats supported by MarkItDown."""

SUPPORTED_DATA_FORMATS = {".csv", ".tsv", ".json", ".xml"}
"""Set[str]: Data file formats supported by MarkItDown."""

SUPPORTED_EBOOK_FORMATS = {".epub"}
"""Set[str]: E-book formats supported by MarkItDown."""


def get_all_supported_formats() -> set[str]:
    """
    Get the complete set of all supported file formats.

    Returns:
        Set of all supported file extensions
    """
    return (
        SUPPORTED_PDF_FORMATS
        | SUPPORTED_IMAGE_FORMATS
        | SUPPORTED_OFFICE_FORMATS
        | SUPPORTED_TEXT_FORMATS
        | SUPPORTED_OPENDOC_FORMATS
        | SUPPORTED_DATA_FORMATS
        | SUPPORTED_EBOOK_FORMATS
    )


def get_ocr_supported_formats() -> set[str]:
    """
    Get file formats that can be processed by OCR.

    Returns:
        Set of OCR-supported file extensions
    """
    return SUPPORTED_PDF_FORMATS | SUPPORTED_IMAGE_FORMATS | SUPPORTED_OFFICE_FORMATS
