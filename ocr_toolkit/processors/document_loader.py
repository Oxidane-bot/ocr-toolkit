"""
Document loader for OCR processing.

This module provides a high-cohesion loader for various document formats,
handling format detection, conversion, and loading into DocumentFile objects.
"""

import logging
from pathlib import Path

from doctr.io import DocumentFile

from ..converters import get_office_converter
from ..utils import get_path_normalizer
from .base import ProcessingResult


class DocumentLoader:
    """
    Handler for loading documents of various formats.

    This class encapsulates document loading logic including:
    - Format detection and validation
    - Path normalization for cross-platform compatibility
    - Office document to PDF conversion
    - Image and PDF loading
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

    def load_document(self, file_path: str, result: ProcessingResult | None = None) -> DocumentFile | None:
        """
        Load document file for OCR processing.

        Args:
            file_path: Path to the document
            result: Optional ProcessingResult to update with temp files and errors

        Returns:
            DocumentFile object or None if loading failed
        """
        try:
            ext = Path(file_path).suffix.lower()

            # Validate format
            if not self.is_supported_format(ext):
                error_msg = f'Unsupported file format: {ext}'
                self.logger.error(error_msg)
                if result:
                    result.error = error_msg
                return None

            # Handle Chinese path encoding issues on Windows
            normalized_path = self.path_normalizer.normalize_path(file_path)

            # Load based on format type
            if ext in self.PDF_FORMATS:
                return self._load_pdf(normalized_path)

            elif ext in self.IMAGE_FORMATS:
                return self._load_image(normalized_path)

            elif ext in self.OFFICE_FORMATS:
                return self._load_office_document(normalized_path, file_path, result)

            else:
                error_msg = f'Unsupported format for document loading: {ext}'
                self.logger.error(error_msg)
                if result:
                    result.error = error_msg
                return None

        except Exception as e:
            error_msg = f'Failed to load document: {str(e)}'
            self.logger.error(f"{error_msg} - {file_path}")
            if result:
                result.error = error_msg
            return None

    def _load_pdf(self, normalized_path: str) -> DocumentFile:
        """
        Load PDF document.

        Args:
            normalized_path: Normalized file path

        Returns:
            DocumentFile loaded from PDF
        """
        doc = DocumentFile.from_pdf(normalized_path)
        self.logger.debug(f"Loaded PDF with {len(doc)} pages")
        return doc

    def _load_image(self, normalized_path: str) -> DocumentFile:
        """
        Load image file.

        Args:
            normalized_path: Normalized file path

        Returns:
            DocumentFile loaded from image
        """
        doc = DocumentFile.from_images([normalized_path])
        self.logger.debug("Loaded image for processing")
        return doc

    def _load_office_document(self, normalized_path: str, original_path: str,
                             result: ProcessingResult | None = None) -> DocumentFile | None:
        """
        Load Office document by converting to PDF first.

        Args:
            normalized_path: Normalized file path
            original_path: Original file path (for error messages)
            result: Optional ProcessingResult to update with temp files

        Returns:
            DocumentFile loaded from converted PDF, or None if conversion failed
        """
        # Convert Office document to PDF first
        temp_pdf = self.office_converter.create_temp_pdf(normalized_path)

        if not temp_pdf:
            error_msg = f'Failed to convert Office document to PDF: {original_path}'
            self.logger.error(error_msg)
            if result:
                result.error = error_msg
            return None

        # Track temp file for cleanup
        if result:
            result.temp_files.append(temp_pdf)

        # Load the converted PDF
        doc = DocumentFile.from_pdf(temp_pdf)
        self.logger.debug(f"Converted Office document to PDF with {len(doc)} pages")
        return doc
