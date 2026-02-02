"""
DOCX to PDF conversion strategy using docx2pdf library.
"""

import logging
import time
from typing import Any

from .base import ConversionStrategy


class DocxToPdfStrategy(ConversionStrategy):
    """
    Strategy for converting DOCX files using docx2pdf library.

    This is the fastest method for .docx files but requires the docx2pdf
    library to be installed.
    """

    def convert(self, input_path: str, output_path: str) -> dict[str, Any]:
        """
        Convert DOCX to PDF using docx2pdf library.

        Args:
            input_path: Path to input DOCX file
            output_path: Path to output PDF file

        Returns:
            Dictionary with conversion results
        """
        result = {
            "method": self.get_method_name(),
            "success": False,
            "processing_time": 0,
            "error": "",
        }

        start_time = time.time()

        try:
            from docx2pdf import convert

            convert(input_path, output_path)
            result["success"] = True
            logging.info(f"Successfully converted {input_path} to PDF using docx2pdf")

        except Exception as e:
            result["error"] = str(e)
            logging.error(f"docx2pdf conversion failed for {input_path}: {e}")

        result["processing_time"] = time.time() - start_time
        return result

    def supports_format(self, file_extension: str) -> bool:
        """
        Check if this strategy supports the given file format.

        Args:
            file_extension: File extension

        Returns:
            True for .docx files only
        """
        return file_extension.lower() == ".docx"

    def get_method_name(self) -> str:
        """Get the name of this conversion method."""
        return "docx2pdf"
