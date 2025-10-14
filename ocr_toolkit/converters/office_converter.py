"""
Office document conversion module using strategy pattern.

This module provides a clean interface for converting Office documents to PDF
using different conversion strategies, improving maintainability and extensibility.

The module has been refactored following high-cohesion, low-coupling principles:
- Base strategy interface: strategies/base.py
- DOCX conversion: strategies/docx_to_pdf.py
- Word COM conversion: strategies/word_com.py
- PowerPoint COM conversion: strategies/powerpoint_com.py
- Excel COM conversion: strategies/excel_com.py
"""

import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from .strategies import (
    DocxToPdfStrategy,
    ExcelComStrategy,
    PowerPointComStrategy,
    WordComStrategy,
)


class OfficeConverter:
    """
    Office document converter using strategy pattern.

    This class provides a clean interface for converting Office documents to PDF
    by automatically selecting the appropriate conversion strategy.

    Architecture:
    - Uses composition to delegate conversion to specific strategies
    - Supports fallback mechanism (e.g., docx2pdf -> Word COM for .docx)
    - Provides both synchronous conversion and temporary file creation
    """

    def __init__(self):
        """Initialize converter with available strategies."""
        self.strategies = [
            DocxToPdfStrategy(),
            WordComStrategy(),
            PowerPointComStrategy(),
            ExcelComStrategy()
        ]
        self.logger = logging.getLogger(__name__)

    def convert_to_pdf(self, input_path: str, output_path: str) -> dict[str, Any]:
        """
        Convert Office document to PDF using the appropriate strategy.

        Args:
            input_path: Path to input Office file
            output_path: Path to output PDF file

        Returns:
            Dictionary with conversion results containing:
            - method: Name of the conversion method used
            - success: Boolean indicating success
            - processing_time: Time taken in seconds
            - error: Error message if failed
        """
        ext = Path(input_path).suffix.lower()

        # For .docx files, try docx2pdf first, then fall back to COM
        if ext == '.docx':
            return self._convert_docx_with_fallback(input_path, output_path)

        # For other formats, find the appropriate strategy
        for strategy in self.strategies:
            if strategy.supports_format(ext):
                return strategy.convert(input_path, output_path)

        # No strategy found
        return {
            'method': 'unsupported',
            'success': False,
            'processing_time': 0,
            'error': f'Unsupported file format: {ext}'
        }

    def _convert_docx_with_fallback(self, input_path: str, output_path: str) -> dict[str, Any]:
        """
        Convert DOCX with fallback mechanism.

        Tries docx2pdf first (faster), then falls back to Word COM if it fails.

        Args:
            input_path: Path to input DOCX file
            output_path: Path to output PDF file

        Returns:
            Dictionary with conversion results
        """
        # Try docx2pdf first (faster)
        docx_strategy = next(s for s in self.strategies if isinstance(s, DocxToPdfStrategy))
        result = docx_strategy.convert(input_path, output_path)

        if not result['success']:
            self.logger.warning("docx2pdf failed, trying Word COM automation")
            word_strategy = next(s for s in self.strategies if isinstance(s, WordComStrategy))
            result = word_strategy.convert(input_path, output_path)

        return result

    def create_temp_pdf(self, input_path: str) -> str | None:
        """
        Convert Office document to temporary PDF file for OCR processing.

        Args:
            input_path: Path to input Office file

        Returns:
            Path to temporary PDF file, or None if conversion failed
        """
        try:
            # Create temporary PDF file
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_pdf:
                temp_pdf_path = temp_pdf.name

            # Convert to PDF
            result = self.convert_to_pdf(input_path, temp_pdf_path)

            if result['success']:
                self.logger.info(f"Created temporary PDF: {temp_pdf_path}")
                return temp_pdf_path
            else:
                # Clean up failed temp file safely
                try:
                    if os.path.exists(temp_pdf_path):
                        os.remove(temp_pdf_path)
                except Exception:
                    pass
                self.logger.error(f"Failed to convert {input_path} to PDF: {result['error']}")
                return None

        except Exception as e:
            self.logger.error(f"Error creating temporary PDF for {input_path}: {e}")
            return None

    def get_supported_formats(self) -> list[str]:
        """
        Get list of all supported file formats.

        Returns:
            List of supported file extensions (sorted)
        """
        formats = set()
        for strategy in self.strategies:
            if isinstance(strategy, DocxToPdfStrategy):
                formats.add('.docx')
            elif isinstance(strategy, WordComStrategy):
                formats.update(['.doc', '.docx'])
            elif isinstance(strategy, PowerPointComStrategy):
                formats.update(['.ppt', '.pptx'])
            elif isinstance(strategy, ExcelComStrategy):
                formats.update(['.xls', '.xlsx'])

        return sorted(formats)


# Singleton instance for global use
_office_converter = None


def get_office_converter() -> OfficeConverter:
    """
    Get the global Office converter instance (singleton pattern).

    Returns:
        Global OfficeConverter instance
    """
    global _office_converter
    if _office_converter is None:
        _office_converter = OfficeConverter()
    return _office_converter


# Backward compatibility functions
def convert_office_to_pdf(input_path: str, output_path: str) -> dict[str, Any]:
    """
    Convert Office document to PDF (backward compatibility function).

    Args:
        input_path: Path to input Office file
        output_path: Path to output PDF file

    Returns:
        Dictionary with conversion results
    """
    return get_office_converter().convert_to_pdf(input_path, output_path)


def create_temp_pdf(input_path: str) -> str | None:
    """
    Create temporary PDF from Office document (backward compatibility function).

    Args:
        input_path: Path to input Office file

    Returns:
        Path to temporary PDF file, or None if conversion failed
    """
    return get_office_converter().create_temp_pdf(input_path)
