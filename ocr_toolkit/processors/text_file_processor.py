"""
Text file processor for direct content reading.

This module provides a specialized processor for text files that don't require OCR,
handling various text encodings and formats.
"""

import logging
import os
from pathlib import Path

from ..utils import get_path_normalizer


class TextFileProcessor:
    """
    Processor for text files that don't require OCR.

    This class handles:
    - Multiple text encodings (UTF-8, GBK, etc.)
    - Markdown format preservation
    - Text file format detection
    """

    # Supported text file formats
    SUPPORTED_FORMATS = {".txt", ".md", ".rtf"}

    def __init__(self):
        """Initialize text file processor."""
        self.logger = logging.getLogger(__name__)
        self.path_normalizer = get_path_normalizer()

    @classmethod
    def supports_format(cls, file_extension: str) -> bool:
        """
        Check if the given file format is supported.

        Args:
            file_extension: File extension to check (with or without dot)

        Returns:
            True if format is supported, False otherwise
        """
        ext = file_extension.lower()
        if not ext.startswith("."):
            ext = "." + ext
        return ext in cls.SUPPORTED_FORMATS

    def process_file(self, file_path: str) -> str:
        """
        Process text file by reading its content directly.

        Args:
            file_path: Path to the text file

        Returns:
            File content as markdown string

        Raises:
            Exception: If file cannot be read with any supported encoding
        """
        ext = Path(file_path).suffix.lower()

        if not self.supports_format(ext):
            raise ValueError(f"Unsupported text format: {ext}")

        try:
            # Handle Chinese path encoding issues on Windows
            normalized_path = self.path_normalizer.normalize_path(file_path)

            # Try UTF-8 first (most common)
            try:
                content = self._read_file(normalized_path, "utf-8")
                self.logger.debug(f"Successfully read {file_path} with UTF-8 encoding")
            except UnicodeDecodeError:
                # Fallback to GBK for Chinese files
                content = self._read_file(normalized_path, "gbk")
                self.logger.debug(f"Successfully read {file_path} with GBK encoding")

            # Format based on file type
            return self._format_content(content, file_path, ext)

        except Exception as e:
            self.logger.error(f"Failed to read text file {file_path}: {e}")
            raise

    def _read_file(self, file_path: str, encoding: str) -> str:
        """
        Read file with specified encoding.

        Args:
            file_path: Path to file
            encoding: Character encoding to use

        Returns:
            File content as string

        Raises:
            UnicodeDecodeError: If encoding doesn't match file
        """
        with open(file_path, encoding=encoding) as f:
            return f.read()

    def _format_content(self, content: str, file_path: str, ext: str) -> str:
        """
        Format file content as markdown.

        Args:
            content: File content
            file_path: Original file path
            ext: File extension

        Returns:
            Formatted markdown string
        """
        # For markdown files, return content as-is
        if ext == ".md":
            return content

        # For other text files, wrap in markdown format with filename as header
        filename = os.path.basename(file_path)
        return f"# {filename}\n\n{content}"

    def get_supported_encodings(self) -> list[str]:
        """
        Get list of supported text encodings.

        Returns:
            List of encoding names
        """
        return ["utf-8", "gbk"]
