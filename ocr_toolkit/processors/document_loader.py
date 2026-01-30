"""
Document loader for OCR processing.

This module provides a high-cohesion loader for Office document conversion.
PaddleOCR-VL handles PDF and image loading directly, so this loader focuses
on Office document to PDF conversion.
"""

import logging
from pathlib import Path

from ..converters import get_office_converter
from ..utils import get_path_normalizer
from ..utils.profiling import Profiler
from .base import ProcessingResult


class DocumentLoader:
    """
    Handler for loading documents of various formats.

    This class encapsulates Office document to PDF conversion.
    PaddleOCR-VL handles PDF and image loading directly.

    Note: This is kept for Office document conversion only.
    PDF and image formats are handled directly by PaddleOCR-VL.
    """

    # Supported formats grouped by type
    PDF_FORMATS = {'.pdf'}
    IMAGE_FORMATS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.gif'}
    OFFICE_FORMATS = {'.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx'}
    TEXT_FORMATS = {'.txt', '.md', '.rtf'}

    def __init__(self):
        """Initialize document loader with required utilities."""
        self.logger = logging.getLogger(__name__)
        self.office_converter = get_office_converter()
        self.path_normalizer = get_path_normalizer()

    @classmethod
    def get_supported_formats(cls) -> list[str]:
        """
        Get list of all supported file formats.

        Returns:
            List of supported file extensions (lowercase, with dot)
        """
        all_formats = (
            cls.PDF_FORMATS |
            cls.IMAGE_FORMATS |
            cls.OFFICE_FORMATS |
            cls.TEXT_FORMATS
        )
        return sorted(all_formats)

    @classmethod
    def is_supported_format(cls, file_extension: str) -> bool:
        """
        Check if the given file format is supported.

        Args:
            file_extension: File extension to check (with or without dot)

        Returns:
            True if format is supported, False otherwise
        """
        ext = file_extension.lower()
        if not ext.startswith('.'):
            ext = '.' + ext

        return ext in cls.get_supported_formats()

    @classmethod
    def is_text_format(cls, file_extension: str) -> bool:
        """
        Check if the given file format is a text format.

        Args:
            file_extension: File extension to check

        Returns:
            True if format is a text format, False otherwise
        """
        return file_extension.lower() in cls.TEXT_FORMATS
